"""Orchestrates one full validation run: validate, resolve, walk-forward, Monte Carlo, analyze, compile.

`ValidationRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `ValidationSession` is the outcome record of one run
attempt, mirroring `app.optimization_engine.runner.OptimizationSession`'s
"never raises, inspect `.is_successful`" shape via `try_execute`, plus a
raising `execute()` for callers that prefer exceptions.

This runner never optimizes (it never calls `app.optimization_engine`'s
search methods) and never backtests independently (every simulated
statistic comes from a real `BacktestRunner.execute()` call; Monte Carlo
resamples an already-produced trade list instead of simulating new ones).
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.exceptions import BacktestingEngineError
from app.backtesting_engine.runner import BacktestRunner
from app.core.base_engine import BaseEngine
from app.indicator_engine.exceptions import IndicatorEngineError
from app.smart_money_engine.exceptions import SMCEngineError
from app.validation_engine.analysis import ConfidenceAnalyzer, RobustnessAnalyzer, StabilityAnalyzer
from app.validation_engine.compiler import ValidationCompiler
from app.validation_engine.context import ValidationContext
from app.validation_engine.exceptions import ValidationConfigurationError, ValidationExecutionError, ValidationValidationError
from app.validation_engine.models import ConfidenceScore, MonteCarloResult, RobustnessScore, StabilityScore, ValidationResult, WalkForwardResult
from app.validation_engine.monte_carlo import MonteCarloEngine
from app.validation_engine.resolve import resolve_candidate
from app.validation_engine.validator import ValidationCheckResult, ValidationIssue, ValidationValidator
from app.validation_engine.walk_forward import WalkForwardEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ValidationSession:
    """The outcome record of one `ValidationRunner.try_execute()` call."""

    session_id: str
    context: ValidationContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ValidationCheckResult | None = None
    result: ValidationResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseValidationRunner(BaseEngine, ABC):
    """Common contract every validation-running engine implements."""

    name = "BaseValidationRunner"

    @abstractmethod
    def execute(self, context: ValidationContext) -> ValidationResult:
        """Run a validation and return its `ValidationResult`.

        Raises:
            ValidationValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> ValidationResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class ValidationRunner(BaseValidationRunner):
    """The default `BaseValidationRunner` implementation."""

    name = "ValidationRunner"

    def __init__(
        self,
        validator: ValidationValidator | None = None,
        backtest_runner: BacktestRunner | None = None,
        walk_forward_engine: WalkForwardEngine | None = None,
        monte_carlo_engine: MonteCarloEngine | None = None,
        robustness_analyzer: RobustnessAnalyzer | None = None,
        confidence_analyzer: ConfidenceAnalyzer | None = None,
        stability_analyzer: StabilityAnalyzer | None = None,
        compiler: ValidationCompiler | None = None,
    ) -> None:
        self._validator = validator or ValidationValidator()
        self._backtest_runner = backtest_runner or BacktestRunner()
        self._walk_forward_engine = walk_forward_engine or WalkForwardEngine(self._backtest_runner)
        self._monte_carlo_engine = monte_carlo_engine or MonteCarloEngine()
        self._robustness_analyzer = robustness_analyzer or RobustnessAnalyzer()
        self._confidence_analyzer = confidence_analyzer or ConfidenceAnalyzer()
        self._stability_analyzer = stability_analyzer or StabilityAnalyzer()
        self._compiler = compiler or ValidationCompiler()

    def execute(self, context: ValidationContext) -> ValidationResult:
        """Run a validation, raising on validation failure.

        Raises:
            ValidationValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise ValidationValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: ValidationContext) -> ValidationSession:
        """Validate, resolve, run walk-forward/Monte Carlo, analyze, and compile `context`. Never raises."""
        session = ValidationSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Validation session %s failed validation.", session.session_id)
            return session

        try:
            resolved = resolve_candidate(context)

            walk_forward_result: WalkForwardResult | None = None
            robustness_score: RobustnessScore | None = None
            if context.configuration.run_walk_forward:
                assert context.configuration.walk_forward is not None  # guaranteed by validation
                walk_forward_result = self._walk_forward_engine.run(
                    context.data, resolved.strategy_model, resolved.configuration, context.configuration.walk_forward,
                    context.indicator_engine, context.smart_money_engine,
                )
                robustness_score = self._robustness_analyzer.analyze(walk_forward_result)

            monte_carlo_result: MonteCarloResult | None = None
            confidence_score: ConfidenceScore | None = None
            if context.configuration.run_monte_carlo:
                assert context.configuration.monte_carlo is not None  # guaranteed by validation
                full_period_result = self._backtest_runner.execute(
                    BacktestContext(
                        strategy_model=resolved.strategy_model,
                        data=context.data,
                        configuration=resolved.configuration,
                        indicator_engine=context.indicator_engine,
                        smart_money_engine=context.smart_money_engine,
                    )
                )
                monte_carlo_result = self._monte_carlo_engine.run(
                    full_period_result.trades, resolved.configuration.initial_balance, context.configuration.monte_carlo
                )
                confidence_score = self._confidence_analyzer.analyze(monte_carlo_result)

            stability_score = self._stability_analyzer.analyze(robustness_score, context.optimization_result, resolved.outcome)

            result = self._compiler.compile(context, resolved, walk_forward_result, monte_carlo_result, robustness_score, confidence_score, stability_score)
        except (BacktestingEngineError, IndicatorEngineError, SMCEngineError, ValidationConfigurationError, ValidationExecutionError) as exc:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Validation session %s failed execution: %s", session.session_id, exc)
            session.validation = ValidationCheckResult(errors=[ValidationIssue(path="execution", message=str(exc))])
            return session

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Validation session %s completed.", session.session_id)
        return session
