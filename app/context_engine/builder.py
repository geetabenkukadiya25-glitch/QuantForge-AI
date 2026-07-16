"""Builds `ContextSnapshot`s from scalar market facts.

`ContextBuilder` never touches raw OHLCV data or a data source directly
-- callers (a future engine that already has historical/live data loaded)
supply the scalar facts (current datetime, candle index, symbol spec) and
the builder packages them into the standardized `ContextSnapshot`. This
keeps the data flow explicit: `Data Engine -> caller -> ContextBuilder ->
ContextSnapshot -> decision engine`, never `Data Engine -> decision
engine` directly.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.context_engine.exceptions import ContextBuildError
from app.context_engine.models import (
    ContextSnapshot,
    MarketContext,
    MarketStatePlaceholders,
    SessionContext,
    SymbolContext,
    TimeContext,
    TimeframeContext,
)
from app.context_engine.sessions import get_active_session, is_market_open, is_weekend, to_utc
from app.context_engine.version import CONTEXT_VERSION
from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.utils.logger import get_logger

logger = get_logger(__name__)

#: Registered here (not auto-enabled) so `ContextBuilder` can gate the
#: still-unimplemented market-state section behind the platform's
#: Feature Flag System, per `PROJECT_VISION.md`.
MARKET_STATE_PLACEHOLDERS_FLAG = FeatureFlag(
    name="market_state_placeholders",
    stage=FeatureStage.EXPERIMENTAL,
    description="Attach the (still-empty) trend/volatility/liquidity/structure/bias/momentum "
    "placeholder section to built context snapshots.",
    enabled_by_default=False,
)

_REQUIRED_SYMBOL_SPEC_FIELDS = (
    "digits",
    "point",
    "tick_size",
    "tick_value",
    "spread",
    "contract_size",
    "currency",
)


class ContextBuilder:
    """Builds a `ContextSnapshot` from symbol/timeframe/time/session facts."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        if not self._feature_flags.is_registered(MARKET_STATE_PLACEHOLDERS_FLAG.name):
            self._feature_flags.register(MARKET_STATE_PLACEHOLDERS_FLAG)

    def build(
        self,
        *,
        symbol: str,
        timeframe: str,
        current_datetime: datetime,
        candle_index: int,
        symbol_spec: dict[str, Any],
        timezone_name: str = "UTC",
        broker_time: datetime | None = None,
        higher_timeframe: str | None = None,
        lower_timeframe: str | None = None,
    ) -> ContextSnapshot:
        """Build a `ContextSnapshot` from the given scalar market facts.

        Raises:
            ContextBuildError: if `symbol_spec` is missing required keys.
        """
        missing = [f for f in _REQUIRED_SYMBOL_SPEC_FIELDS if f not in symbol_spec]
        if missing:
            raise ContextBuildError(f"symbol_spec is missing required field(s): {missing}")

        moment_utc = to_utc(current_datetime)

        time_context = self._build_time_context(moment_utc)
        session_context = self._build_session_context(moment_utc)
        symbol_context = SymbolContext(symbol=symbol, **symbol_spec)
        timeframe_context = TimeframeContext(
            current=timeframe, higher_timeframe=higher_timeframe, lower_timeframe=lower_timeframe
        )
        market_context = MarketContext(
            symbol=symbol,
            timeframe=timeframe,
            candle_index=candle_index,
            datetime_utc=moment_utc,
            broker_time=broker_time,
            timezone=timezone_name,
            session=session_context,
        )

        state = (
            MarketStatePlaceholders()
            if self._feature_flags.is_enabled(MARKET_STATE_PLACEHOLDERS_FLAG.name)
            else None
        )

        snapshot = ContextSnapshot(
            snapshot_id=str(uuid.uuid4()),
            context_version=CONTEXT_VERSION,
            created_at=datetime.now(timezone.utc),
            market=market_context,
            time=time_context,
            symbol=symbol_context,
            timeframe=timeframe_context,
            state=state,
        )
        logger.info(
            "Built context snapshot %s for %s %s @ %s (candle_index=%d)",
            snapshot.snapshot_id,
            symbol,
            timeframe,
            moment_utc.isoformat(),
            candle_index,
        )
        return snapshot

    @staticmethod
    def _build_time_context(moment_utc: datetime) -> TimeContext:
        iso_year, iso_week, _ = moment_utc.isocalendar()
        return TimeContext(
            day=moment_utc.day,
            day_of_week=moment_utc.strftime("%A"),
            week=iso_week,
            month=moment_utc.month,
            quarter=(moment_utc.month - 1) // 3 + 1,
            year=iso_year,
        )

    @staticmethod
    def _build_session_context(moment_utc: datetime) -> SessionContext:
        active = get_active_session(moment_utc)
        return SessionContext(
            session_name=active.name,
            session_progress_pct=active.progress_pct,
            session_open=active.session_open,
            session_close=active.session_close,
            is_market_open=is_market_open(moment_utc),
            is_weekend=is_weekend(moment_utc),
        )
