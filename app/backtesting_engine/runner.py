"""Orchestrates one full backtest run: validate, simulate, analyze, compile.

`BacktestRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `BacktestSession` is the outcome record of one run attempt,
mirroring `app.strategy_builder.result.StrategyResult`'s "never raises,
inspect `.is_successful`" shape via `try_execute`, plus a raising
`execute()` for callers that prefer exceptions.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.backtesting_engine.compiler import BacktestCompiler
from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.exceptions import BacktestValidationError
from app.backtesting_engine.models import BacktestResult
from app.backtesting_engine.simulator import ProgressCallback, TradeSimulator
from app.backtesting_engine.statistics import StatisticsEngine
from app.backtesting_engine.validator import BacktestValidator, ValidationResult
from app.core.base_engine import BaseEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class BacktestSession:
    """The outcome record of one `BacktestRunner.try_execute()` call."""

    session_id: str
    context: BacktestContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ValidationResult | None = None
    result: BacktestResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseBacktestRunner(BaseEngine, ABC):
    """Common contract every backtest-running engine implements."""

    name = "BaseBacktestRunner"

    @abstractmethod
    def execute(self, context: BacktestContext) -> BacktestResult:
        """Run a backtest and return its `BacktestResult`.

        Raises:
            BacktestValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> BacktestResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class BacktestRunner(BaseBacktestRunner):
    """The default `BaseBacktestRunner` implementation: validate, simulate, analyze, compile."""

    name = "BacktestRunner"

    def __init__(
        self,
        validator: BacktestValidator | None = None,
        simulator: TradeSimulator | None = None,
        statistics_engine: StatisticsEngine | None = None,
        compiler: BacktestCompiler | None = None,
    ) -> None:
        self._validator = validator or BacktestValidator()
        self._simulator = simulator or TradeSimulator()
        self._statistics_engine = statistics_engine or StatisticsEngine()
        self._compiler = compiler or BacktestCompiler()

    def execute(self, context: BacktestContext, progress_callback: ProgressCallback | None = None) -> BacktestResult:
        """Run a backtest, raising on validation failure.

        `progress_callback`, if given, is called periodically during candle
        simulation as `callback(current_candle, total_candles, current_operation)`
        -- purely observational, never affects the result. Backward compatible:
        omitting it reproduces prior behavior exactly.

        Raises:
            BacktestValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context, progress_callback=progress_callback)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise BacktestValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: BacktestContext, progress_callback: ProgressCallback | None = None) -> BacktestSession:
        """Validate, simulate, analyze, and (if valid) compile `context`. Never raises.

        `progress_callback`, if given, is called periodically during candle
        simulation -- see `execute()`. Optional and backward compatible.
        """
        session = BacktestSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Backtest session %s failed validation.", session.session_id)
            return session

        simulation = self._simulator.run(context, progress_callback=progress_callback)
        drawdown_report, statistics = self._statistics_engine.compute(
            simulation.trades, simulation.equity_curve, context.configuration.risk_free_rate
        )
        result = self._compiler.compile(context, simulation, drawdown_report, statistics)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Backtest session %s completed (%d trade(s)).", session.session_id, len(result.trades))
        return session
