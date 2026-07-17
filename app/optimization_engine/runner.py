"""Orchestrates one full optimization run: validate, generate, evaluate, rank, compile.

`OptimizationRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `OptimizationSession` is the outcome record of one run
attempt, mirroring `app.backtesting_engine.runner.BacktestSession`'s
"never raises, inspect `.is_successful`" shape via `try_execute`, plus a
raising `execute()` for callers that prefer exceptions.

Every candidate is evaluated through the real, unmodified Backtesting
Engine (`BacktestRunner`) -- this module never simulates a trade itself.
A single candidate's failure (e.g. a parameter combination the
Backtesting Engine rejects at validation) is recorded as a failed
outcome and does not abort the run.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.exceptions import BacktestingEngineError
from app.backtesting_engine.runner import BacktestRunner
from app.core.base_engine import BaseEngine
from app.indicator_engine.exceptions import IndicatorEngineError
from app.optimization_engine import objectives
from app.optimization_engine.compiler import OptimizationCompiler
from app.optimization_engine.context import OptimizationContext
from app.optimization_engine.exceptions import (
    OptimizationConfigurationError,
    OptimizationExecutionError,
    OptimizationValidationError,
)
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.models import (
    OptimizationCandidate,
    OptimizationCandidateOutcome,
    OptimizationHistory,
    OptimizationResult,
    OptimizationStatistics,
    SearchMethod,
)
from app.optimization_engine.search import BaseOptimizer, GridSearchOptimizer, RandomSearchOptimizer
from app.optimization_engine.validator import OptimizationValidator, ValidationResult
from app.smart_money_engine.exceptions import SMCEngineError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_OPTIMIZERS: dict[SearchMethod, BaseOptimizer] = {
    SearchMethod.GRID: GridSearchOptimizer(),
    SearchMethod.RANDOM: RandomSearchOptimizer(),
}


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class OptimizationSession:
    """The outcome record of one `OptimizationRunner.try_execute()` call."""

    session_id: str
    context: OptimizationContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ValidationResult | None = None
    result: OptimizationResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseOptimizationRunner(BaseEngine, ABC):
    """Common contract every optimization-running engine implements."""

    name = "BaseOptimizationRunner"

    @abstractmethod
    def execute(self, context: OptimizationContext) -> OptimizationResult:
        """Run an optimization and return its `OptimizationResult`.

        Raises:
            OptimizationValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> OptimizationResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class OptimizationRunner(BaseOptimizationRunner):
    """The default `BaseOptimizationRunner` implementation: validate, generate, evaluate, rank, compile."""

    name = "OptimizationRunner"

    def __init__(
        self,
        validator: OptimizationValidator | None = None,
        backtest_runner: BacktestRunner | None = None,
        compiler: OptimizationCompiler | None = None,
    ) -> None:
        self._validator = validator or OptimizationValidator()
        self._backtest_runner = backtest_runner or BacktestRunner()
        self._compiler = compiler or OptimizationCompiler()

    def execute(self, context: OptimizationContext) -> OptimizationResult:
        """Run an optimization, raising on validation failure.

        Raises:
            OptimizationValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise OptimizationValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: OptimizationContext) -> OptimizationSession:
        """Validate, generate, evaluate, rank, and (if valid) compile `context`. Never raises."""
        session = OptimizationSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Optimization session %s failed validation.", session.session_id)
            return session

        optimizer = _OPTIMIZERS[context.configuration.search_method]
        candidates = optimizer.generate(context.parameter_space, context.configuration)

        entries = tuple(self._evaluate(context, candidate) for candidate in candidates)
        entries = self._rank(entries, context.configuration.objective)
        history = OptimizationHistory(entries=entries)
        statistics = self._summarize(entries, context.configuration.objective)

        result = self._compiler.compile(context, candidates, history, statistics)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Optimization session %s completed (%d candidate(s)).", session.session_id, len(candidates))
        return session

    def _evaluate(self, context: OptimizationContext, candidate: OptimizationCandidate) -> OptimizationCandidateOutcome:
        import json

        values = json.loads(candidate.parameters_json)
        try:
            candidate_model = ParameterGenerator.apply_to_model(context.base_strategy_model, values)
            candidate_configuration = ParameterGenerator.apply_to_configuration(context.base_configuration, values)

            backtest_context = BacktestContext(
                strategy_model=candidate_model,
                data=context.data,
                configuration=candidate_configuration,
                indicator_engine=context.indicator_engine,
                smart_money_engine=context.smart_money_engine,
            )
            backtest_result = self._backtest_runner.execute(backtest_context)
            candidate_score = objectives.score(context.configuration.objective, backtest_result.statistics, context.custom_scorer)

            return OptimizationCandidateOutcome(
                candidate_id=candidate.candidate_id,
                parameters_json=candidate.parameters_json,
                succeeded=True,
                strategy_model_id=candidate_model.model_id,
                strategy_checksum=candidate_model.checksum,
                backtest_checksum=backtest_result.checksum,
                statistics=backtest_result.statistics,
                score=candidate_score,
            )
        except (
            BacktestingEngineError,
            IndicatorEngineError,
            SMCEngineError,
            OptimizationExecutionError,
            OptimizationConfigurationError,
            PydanticValidationError,
        ) as exc:
            logger.warning("Candidate %s failed evaluation: %s", candidate.candidate_id, exc)
            return OptimizationCandidateOutcome(
                candidate_id=candidate.candidate_id,
                parameters_json=candidate.parameters_json,
                succeeded=False,
                error_message=str(exc),
            )

    @staticmethod
    def _rank(entries: tuple[OptimizationCandidateOutcome, ...], objective) -> tuple[OptimizationCandidateOutcome, ...]:
        scored_ids = sorted(
            (e.candidate_id for e in entries if e.succeeded and e.score is not None),
            key=lambda cid: next(e.score for e in entries if e.candidate_id == cid),
            reverse=True,
        )
        rank_by_id = {cid: rank + 1 for rank, cid in enumerate(scored_ids)}
        return tuple(e.model_copy(update={"rank": rank_by_id.get(e.candidate_id)}) for e in entries)

    @staticmethod
    def _summarize(entries: tuple[OptimizationCandidateOutcome, ...], objective) -> OptimizationStatistics:
        scored = [e.score for e in entries if e.succeeded and e.score is not None]
        best_entry = next((e for e in entries if e.rank == 1), None)
        return OptimizationStatistics(
            total_candidates=len(entries),
            evaluated_candidates=sum(1 for e in entries if e.succeeded),
            failed_candidates=sum(1 for e in entries if not e.succeeded),
            objective=objective,
            best_score=max(scored) if scored else None,
            worst_score=min(scored) if scored else None,
            mean_score=(sum(scored) / len(scored)) if scored else None,
            best_candidate_id=best_entry.candidate_id if best_entry else None,
        )
