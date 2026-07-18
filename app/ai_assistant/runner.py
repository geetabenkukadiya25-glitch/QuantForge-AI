"""Orchestrates one full assistant query: validate, classify intent, plan,
reason, recommend, compile.

`AssistantRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `AssistantSession` is the outcome record of one query
attempt, mirroring every prior engine's "never raises, inspect
`.is_successful`" shape via `try_execute`, plus a raising `execute()` for
callers that prefer exceptions.

This runner is read-only: it never executes a trade, never optimizes,
never validates, never replays, never rebuilds a strategy, and never
connects to a broker, MT5, or an external AI service.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.ai_assistant.compiler import AssistantCompiler
from app.ai_assistant.context import AssistantContext
from app.ai_assistant.exceptions import AssistantValidationError
from app.ai_assistant.intent import IntentClassifier
from app.ai_assistant.knowledge import KnowledgeLookup
from app.ai_assistant.models import AssistantResult
from app.ai_assistant.planner import QueryPlanner
from app.ai_assistant.reasoning import ReasoningEngine
from app.ai_assistant.recommendations import RecommendationEngine
from app.ai_assistant.search import SearchEngine
from app.ai_assistant.statistics import AssistantStatisticsEngine
from app.ai_assistant.validator import AssistantCheckResult, AssistantValidator
from app.core.base_engine import BaseEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AssistantSession:
    """The outcome record of one `AssistantRunner.try_execute()` call."""

    session_id: str
    context: AssistantContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: AssistantCheckResult | None = None
    result: AssistantResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseAssistantRunner(BaseEngine, ABC):
    """Common contract every query-answering engine implements."""

    name = "BaseAssistantRunner"

    @abstractmethod
    def execute(self, context: AssistantContext) -> AssistantResult:
        """Answer one query and return its `AssistantResult`.

        Raises:
            AssistantValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> AssistantResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class AssistantRunner(BaseAssistantRunner):
    """The default `BaseAssistantRunner` implementation."""

    name = "AssistantRunner"

    def __init__(
        self,
        validator: AssistantValidator | None = None,
        intent_classifier: IntentClassifier | None = None,
        planner: QueryPlanner | None = None,
        search_engine: SearchEngine | None = None,
        knowledge_lookup: KnowledgeLookup | None = None,
        statistics_engine: AssistantStatisticsEngine | None = None,
        reasoning_engine: ReasoningEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        compiler: AssistantCompiler | None = None,
    ) -> None:
        self._validator = validator or AssistantValidator()
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._planner = planner or QueryPlanner()
        search_engine = search_engine or SearchEngine()
        knowledge_lookup = knowledge_lookup or KnowledgeLookup()
        statistics_engine = statistics_engine or AssistantStatisticsEngine()
        self._reasoning_engine = reasoning_engine or ReasoningEngine(search_engine, knowledge_lookup, statistics_engine)
        self._recommendation_engine = recommendation_engine or RecommendationEngine(search_engine)
        self._compiler = compiler or AssistantCompiler()

    def execute(self, context: AssistantContext) -> AssistantResult:
        """Answer one query, raising on validation failure.

        Raises:
            AssistantValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise AssistantValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: AssistantContext) -> AssistantSession:
        """Validate, classify, plan, reason, recommend, and compile `context`. Never raises."""
        session = AssistantSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Assistant session %s failed validation.", session.session_id)
            return session

        classification = self._intent_classifier.classify(context.query)
        self._planner.plan(classification.intent)  # available for future multi-pass planning; current reasoning is single-pass

        answer = self._reasoning_engine.answer(context, classification)
        recommendations = self._recommendation_engine.recommend(context, answer)
        answer = answer.model_copy(update={"recommendations": recommendations})

        result = self._compiler.compile(context, answer)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Assistant session %s completed (intent=%s).", session.session_id, classification.intent.value)
        return session
