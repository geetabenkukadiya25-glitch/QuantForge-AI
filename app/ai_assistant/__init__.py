"""AI Research Assistant.

A deterministic, offline research assistant that helps users explore and
understand data already present inside QuantForge AI -- NOT an LLM. It
NEVER connects to any external AI API or service, and NEVER requires
internet access. No embeddings, no vector database.
Every answer traces back to an id already present in an attached
registry (Knowledge Base, Research Engine, Portfolio Engine, Strategy
Library, Indicator Engine, Smart Money Engine) or this module's own
static, documentation-sourced glossary -- never a generated or
hallucinated claim. It is strictly read-only: it NEVER executes a trade,
NEVER optimizes, NEVER validates, NEVER replays, NEVER rebuilds a
strategy, and NEVER connects to a broker or MT5.

This is the official Phase 15 of `PROJECT_VISION.md`'s Approved Roadmap.
"""

from app.ai_assistant.compiler import AssistantCompiler
from app.ai_assistant.context import AssistantContext
from app.ai_assistant.conversation import ConversationManager, ConversationSession, ConversationTurn
from app.ai_assistant.engine import AIResearchAssistantEngine
from app.ai_assistant.exceptions import (
    AssistantConfigurationError,
    AssistantDisabledError,
    AssistantEngineError,
    AssistantExecutionError,
    AssistantNotFoundError,
    AssistantRegistrationError,
    AssistantValidationError,
)
from app.ai_assistant.intent import IntentClassifier
from app.ai_assistant.knowledge import ENGINE_GLOSSARY, KnowledgeLookup
from app.ai_assistant.metadata import AI_ASSISTANT_RESULT_VERSION, AssistantMetadata
from app.ai_assistant.models import (
    AnswerSection,
    AssistantAnswer,
    AssistantConfiguration,
    AssistantResult,
    IntentClassification,
    QueryIntent,
    RecommendationItem,
    SearchResultItem,
    SearchSourceType,
)
from app.ai_assistant.planner import QueryPlanner
from app.ai_assistant.reasoning import ReasoningEngine
from app.ai_assistant.recommendations import RecommendationEngine
from app.ai_assistant.registry import AssistantRegistry
from app.ai_assistant.report import AssistantReport
from app.ai_assistant.runner import BaseAssistantRunner, AssistantRunner, AssistantSession, SessionStatus
from app.ai_assistant.search import SearchEngine
from app.ai_assistant.serializer import AssistantSerializer
from app.ai_assistant.statistics import AssistantStatisticsEngine
from app.ai_assistant.validator import AssistantCheckResult, AssistantIssue, AssistantValidator

__all__ = [
    "AIResearchAssistantEngine",
    "AssistantRunner",
    "BaseAssistantRunner",
    "AssistantSession",
    "SessionStatus",
    "AssistantContext",
    "AssistantCompiler",
    "AssistantValidator",
    "AssistantCheckResult",
    "AssistantIssue",
    "AssistantSerializer",
    "AssistantRegistry",
    "AssistantReport",
    "AssistantMetadata",
    "AI_ASSISTANT_RESULT_VERSION",
    "AssistantConfiguration",
    "AssistantResult",
    "AssistantAnswer",
    "AnswerSection",
    "SearchResultItem",
    "SearchSourceType",
    "RecommendationItem",
    "IntentClassification",
    "QueryIntent",
    "IntentClassifier",
    "QueryPlanner",
    "KnowledgeLookup",
    "ENGINE_GLOSSARY",
    "SearchEngine",
    "ReasoningEngine",
    "RecommendationEngine",
    "AssistantStatisticsEngine",
    "ConversationManager",
    "ConversationSession",
    "ConversationTurn",
    "AssistantEngineError",
    "AssistantConfigurationError",
    "AssistantValidationError",
    "AssistantExecutionError",
    "AssistantNotFoundError",
    "AssistantDisabledError",
    "AssistantRegistrationError",
]
