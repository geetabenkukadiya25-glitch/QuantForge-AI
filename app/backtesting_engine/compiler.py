"""Compiles simulation artifacts into an immutable `BacktestResult`.

A pure transformation: given a `BacktestContext` and the already-computed
`SimulationOutput`/`DrawdownReport`/`PerformanceStatistics`, build the
final `BacktestResult` and its content checksum. Never touches the
candle loop itself -- that's `TradeSimulator`'s job, run before
compilation.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.metadata import BACKTEST_RESULT_VERSION, BacktestMetadata
from app.backtesting_engine.models import BacktestResult, DrawdownReport, PerformanceStatistics
from app.backtesting_engine.simulator import SimulationOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestCompiler:
    """Builds a `BacktestResult` from one run's simulation output and statistics."""

    def compile(
        self,
        context: BacktestContext,
        simulation: SimulationOutput,
        drawdown_report: DrawdownReport,
        statistics: PerformanceStatistics,
    ) -> BacktestResult:
        strategy_model = context.strategy_model
        metadata = BacktestMetadata(
            backtest_id=str(uuid.uuid4()),
            strategy_id=strategy_model.metadata.id,
            strategy_model_id=strategy_model.model_id,
            strategy_checksum=strategy_model.checksum,
            strategy_model_version=strategy_model.metadata.model_version,
            result_version=BACKTEST_RESULT_VERSION,
        )

        checksum = self._checksum(
            metadata=metadata,
            configuration=context.configuration,
            trades=simulation.trades,
            equity_curve=simulation.equity_curve,
            balance_curve=simulation.balance_curve,
            drawdown_report=drawdown_report,
            statistics=statistics,
            execution_timeline=tuple(simulation.execution_timeline),
        )

        result = BacktestResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            trades=tuple(simulation.trades),
            equity_curve=simulation.equity_curve,
            balance_curve=simulation.balance_curve,
            drawdown_report=drawdown_report,
            statistics=statistics,
            execution_timeline=tuple(simulation.execution_timeline),
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Compiled backtest for strategy '%s' (checksum=%s, %d trade(s))",
            metadata.strategy_id,
            checksum[:12],
            len(result.trades),
        )
        return result

    @staticmethod
    def _checksum(
        metadata: BacktestMetadata,
        configuration,
        trades,
        equity_curve,
        balance_curve,
        drawdown_report,
        statistics,
        execution_timeline,
    ) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.backtest_id`) -- two runs of the
        same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["backtest_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "trades": [t.model_dump(mode="json") for t in trades],
            "equity_curve": equity_curve.model_dump(mode="json"),
            "balance_curve": balance_curve.model_dump(mode="json"),
            "drawdown_report": drawdown_report.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
            "execution_timeline": [e.model_dump(mode="json") for e in execution_timeline],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
