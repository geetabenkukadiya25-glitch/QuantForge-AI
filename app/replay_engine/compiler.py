"""Compiles a validated replay preparation into an immutable `ReplayResult`.

A pure transformation: given a `ReplayContext`, its computed `ReplayTimeline`
and `ReplayStatistics`, and any events already recorded, build the final
`ReplayResult` and its content checksum -- the same discipline
`ValidationCompiler`/`OptimizationCompiler`/`BacktestCompiler` established:
every identity/timestamp field is excluded from the checksum payload before
hashing, so two runs of the same context produce the same checksum.
"""

import uuid
from datetime import datetime, timezone

import pandas as pd

from app.core.checksums import compute_checksum, sha256_hex
from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.replay_engine.context import ReplayContext
from app.replay_engine.metadata import REPLAY_RESULT_VERSION, ReplayMetadata
from app.replay_engine.models import ReplayEvent, ReplayResult, ReplayStatistics, ReplayTimeline
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReplayCompiler:
    """Builds a `ReplayResult` from one replay preparation's timeline and statistics."""

    def compile(
        self,
        context: ReplayContext,
        timeline: ReplayTimeline,
        statistics: ReplayStatistics,
        events: tuple[ReplayEvent, ...] = (),
    ) -> ReplayResult:
        metadata = ReplayMetadata(
            replay_id=str(uuid.uuid4()),
            data_checksum=self._data_checksum(context, timeline),
            strategy_id=context.strategy_model.metadata.id if context.strategy_model else None,
            strategy_model_id=context.strategy_model.model_id if context.strategy_model else None,
            strategy_checksum=context.strategy_model.checksum if context.strategy_model else None,
            backtest_result_id=context.backtest_result.result_id if context.backtest_result else None,
            backtest_checksum=context.backtest_result.checksum if context.backtest_result else None,
            result_version=REPLAY_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, timeline, statistics, events)

        result = ReplayResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            timeline=timeline,
            statistics=statistics,
            events=events,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled replay result for %s %s (checksum=%s)", context.configuration.symbol, context.configuration.timeframe, checksum[:12])
        return result

    @staticmethod
    def _data_checksum(context: ReplayContext, timeline: ReplayTimeline) -> str:
        """A content hash of the exact data slice this replay covers -- not a
        general anti-tamper hash, just a fast, deterministic identity check
        (`pandas.util.hash_pandas_object` is vectorized, unlike hashing the
        full DataFrame through JSON).
        """
        sliced = context.data.iloc[timeline.start_index : timeline.end_index + 1]
        columns = [c for c in (DATETIME_COL, *OHLC_COLS, VOLUME_COL) if c in sliced.columns]
        hashed = pd.util.hash_pandas_object(sliced[columns], index=False)
        total = int(hashed.sum()) & 0xFFFFFFFFFFFFFFFF
        return sha256_hex(str(total))

    @staticmethod
    def _checksum(metadata: ReplayMetadata, configuration, timeline: ReplayTimeline, statistics: ReplayStatistics, events: tuple[ReplayEvent, ...]) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.replay_id`) -- two runs of the
        same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["replay_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "timeline": timeline.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
            "events": [e.model_dump(mode="json") for e in events],
        }
        return compute_checksum(payload)
