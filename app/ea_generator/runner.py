"""Orchestrates one full EA generation: validate, generate, compile.

`EAGeneratorRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `EAGeneratorSession` is the outcome record of one
generation attempt, mirroring `app.portfolio_engine.runner.PortfolioRunner`'s
"never raises, inspect `.is_successful`" shape via `try_execute`, plus a
raising `execute()` for callers that prefer exceptions.

This runner is an OFFLINE CODE GENERATOR ONLY: it never compiles MT5,
never executes trades, never connects to a broker, never calls
MetaTrader, and never calls an external API.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.base_engine import BaseEngine
from app.ea_generator.compiler import EACompiler
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.exceptions import EAValidationError
from app.ea_generator.generator import EAGenerator
from app.ea_generator.models import EAGeneratorResult
from app.ea_generator.statistics import EAGeneratorStatisticsEngine
from app.ea_generator.validator import EAGeneratorCheckResult, EAGeneratorValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class EAGeneratorSession:
    """The outcome record of one `EAGeneratorRunner.try_execute()` call."""

    session_id: str
    context: EAGeneratorContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: EAGeneratorCheckResult | None = None
    result: EAGeneratorResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseEAGeneratorRunner(BaseEngine, ABC):
    """Common contract every EA-generating engine implements."""

    name = "BaseEAGeneratorRunner"

    @abstractmethod
    def execute(self, context: EAGeneratorContext) -> EAGeneratorResult:
        """Generate an EA and return its `EAGeneratorResult`.

        Raises:
            EAValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> EAGeneratorResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class EAGeneratorRunner(BaseEAGeneratorRunner):
    """The default `BaseEAGeneratorRunner` implementation."""

    name = "EAGeneratorRunner"

    def __init__(
        self,
        validator: EAGeneratorValidator | None = None,
        generator: EAGenerator | None = None,
        statistics_engine: EAGeneratorStatisticsEngine | None = None,
        compiler: EACompiler | None = None,
    ) -> None:
        self._validator = validator or EAGeneratorValidator()
        self._generator = generator or EAGenerator()
        self._statistics_engine = statistics_engine or EAGeneratorStatisticsEngine()
        self._compiler = compiler or EACompiler()

    def execute(self, context: EAGeneratorContext) -> EAGeneratorResult:
        """Generate an EA, raising on validation failure.

        Raises:
            EAValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise EAValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: EAGeneratorContext) -> EAGeneratorSession:
        """Validate and generate `context`. Never raises."""
        session = EAGeneratorSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("EA generation session %s failed validation.", session.session_id)
            return session

        artifacts = self._generator.generate(context)
        statistics = self._statistics_engine.compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)

        result = self._compiler.compile(
            context,
            source_code=artifacts.source_code,
            inputs=artifacts.inputs,
            indicator_declarations=artifacts.indicator_declarations,
            risk_parameters=artifacts.risk_parameters,
            trade_management=artifacts.trade_management,
            statistics=statistics,
        )

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("EA generation session %s completed (strategy=%r).", session.session_id, context.strategy_model.metadata.id)
        return session
