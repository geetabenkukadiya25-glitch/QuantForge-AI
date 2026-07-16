"""Market Context data model.

Every model here is immutable (`frozen=True`) and therefore hashable and
serializable -- required for `ContextSnapshot` per the Phase 5 spec. This
module holds *descriptive* data only: no trend/volatility/bias/etc. is
computed, and nothing here ever produces a buy/sell decision. The Market
Context Engine only describes market state; deciding what to do with
that state is a future engine's job, per `PROJECT_VISION.md`'s
"Context Before Decision" principle.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.context_engine.version import CONTEXT_VERSION


class ContextModel(BaseModel):
    """Base class for every context model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class TimeContext(ContextModel):
    """Calendar decomposition of the current moment (UTC).

    `trading_day`/`trading_week`/`trading_month` are explicit placeholders:
    computing them correctly requires a trading-calendar/holiday data
    source that does not exist yet (see `holiday` on `SessionContext`).
    """

    day: int = Field(ge=1, le=31)
    day_of_week: str
    week: int = Field(ge=1, le=53, description="ISO week number.")
    month: int = Field(ge=1, le=12)
    quarter: int = Field(ge=1, le=4)
    year: int

    trading_day: int | None = Field(default=None, description="Placeholder: requires a trading calendar.")
    trading_week: int | None = Field(default=None, description="Placeholder: requires a trading calendar.")
    trading_month: int | None = Field(default=None, description="Placeholder: requires a trading calendar.")


class SessionContext(ContextModel):
    """The trading session active at the current moment, if any."""

    session_name: str | None = None
    session_progress_pct: float | None = Field(default=None, ge=0, le=100)
    session_open: datetime | None = None
    session_close: datetime | None = None
    is_market_open: bool
    is_weekend: bool
    is_holiday: bool | None = Field(default=None, description="Placeholder: no holiday calendar data source yet.")


class SymbolContext(ContextModel):
    """Static instrument specification for the current symbol."""

    symbol: str = Field(min_length=1)
    digits: int = Field(ge=0)
    point: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    tick_value: float = Field(gt=0)
    spread: float = Field(ge=0)
    contract_size: float = Field(gt=0)
    currency: str = Field(min_length=1)


class TimeframeContext(ContextModel):
    """The current timeframe, plus reserved slots for multi-timeframe context."""

    current: str = Field(min_length=1)
    higher_timeframe: str | None = Field(default=None, description="Placeholder for future multi-TF context.")
    lower_timeframe: str | None = Field(default=None, description="Placeholder for future multi-TF context.")


class MarketStatePlaceholders(ContextModel):
    """Reserved market-state fields.

    All placeholders only -- no calculation, no trading logic. Populated
    (still as `None`) only when the experimental
    `market_state_placeholders` feature flag is enabled; future phases
    (Indicator Engine, Smart Money Engine) will implement real values.
    """

    trend_state: str | None = None
    volatility_state: str | None = None
    liquidity_state: str | None = None
    structure_state: str | None = None
    bias_state: str | None = None
    momentum_state: str | None = None


class MarketContext(ContextModel):
    """The core "where/when/what" facts about the current market moment."""

    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    candle_index: int = Field(ge=0)
    datetime_utc: datetime
    broker_time: datetime | None = None
    timezone: str = Field(min_length=1, default="UTC")
    session: SessionContext


class ContextSnapshot(ContextModel):
    """The complete, immutable, versioned Market Context output.

    This is the single object every future decision engine must consume
    instead of touching raw market data directly (SSOT: "Strategies" own
    their rules via SDL; market description is owned here).
    """

    snapshot_id: str = Field(min_length=1)
    context_version: str = Field(default=CONTEXT_VERSION)
    created_at: datetime

    market: MarketContext
    time: TimeContext
    symbol: SymbolContext
    timeframe: TimeframeContext
    state: MarketStatePlaceholders | None = None
