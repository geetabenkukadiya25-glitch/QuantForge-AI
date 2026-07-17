"""Orchestrates one full knowledge base build: validate, compute statistics, compile.

`KnowledgeRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `KnowledgeSession` is the outcome record of one build
attempt, mirroring `app.research_engine.runner.ResearchRunner`'s "never
raises, inspect `.is_successful`" shape via `try_execute`, plus a raising
`execute()` for callers that prefer exceptions.

This runner never executes a trade, never optimizes, never backtests,
never validates, never replays, and never connects to a broker or MT5 --
it only validates and compiles authored content.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.base_engine import BaseEngine
from app.knowledge_base.compiler import KnowledgeCompiler
from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.exceptions import KnowledgeValidationError
from app.knowledge_base.models import KnowledgeResult
from app.knowledge_base.statistics import KnowledgeStatisticsEngine
from app.knowledge_base.validator import KnowledgeCheckResult, KnowledgeValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class KnowledgeSession:
    """The outcome record of one `KnowledgeRunner.try_execute()` call."""

    session_id: str
    context: KnowledgeContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: KnowledgeCheckResult | None = None
    result: KnowledgeResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseKnowledgeRunner(BaseEngine, ABC):
    """Common contract every knowledge-building engine implements."""

    name = "BaseKnowledgeRunner"

    @abstractmethod
    def execute(self, context: KnowledgeContext) -> KnowledgeResult:
        """Build a knowledge base and return its `KnowledgeResult`.

        Raises:
            KnowledgeValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> KnowledgeResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class KnowledgeRunner(BaseKnowledgeRunner):
    """The default `BaseKnowledgeRunner` implementation."""

    name = "KnowledgeRunner"

    def __init__(
        self,
        validator: KnowledgeValidator | None = None,
        statistics_engine: KnowledgeStatisticsEngine | None = None,
        compiler: KnowledgeCompiler | None = None,
    ) -> None:
        self._validator = validator or KnowledgeValidator()
        self._statistics_engine = statistics_engine or KnowledgeStatisticsEngine()
        self._compiler = compiler or KnowledgeCompiler()

    def execute(self, context: KnowledgeContext) -> KnowledgeResult:
        """Build a knowledge base, raising on validation failure.

        Raises:
            KnowledgeValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise KnowledgeValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: KnowledgeContext) -> KnowledgeSession:
        """Validate, compute statistics, and compile `context`. Never raises."""
        session = KnowledgeSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Knowledge session %s failed validation.", session.session_id)
            return session

        statistics = self._statistics_engine.compute(context.entries)
        result = self._compiler.compile(context, statistics)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Knowledge session %s completed (%d entries).", session.session_id, len(context.entries))
        return session
