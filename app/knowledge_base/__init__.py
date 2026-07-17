"""Knowledge Base Platform.

An institutional documentation and trading-knowledge system -- NOT AI,
NOT Strategy Builder, NOT the Research Engine. Stores, indexes, and
serves authored `KnowledgeEntry` content across SMC, ICT, price action,
indicators, patterns, candlesticks, risk management, psychology,
sessions, market structure, and more. It NEVER executes a trade, NEVER
optimizes, NEVER backtests, NEVER validates, NEVER replays, and NEVER
connects to a broker or MT5. Consumes existing outputs only -- it never
rebuilds Strategy Builder, Backtesting, Optimization, Validation, or
Replay logic.
"""

from app.knowledge_base.compiler import KnowledgeCompiler
from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.engine import KnowledgeBaseEngine
from app.knowledge_base.exceptions import (
    KnowledgeBaseError,
    KnowledgeConfigurationError,
    KnowledgeDisabledError,
    KnowledgeExecutionError,
    KnowledgeNotFoundError,
    KnowledgeRegistrationError,
    KnowledgeValidationError,
)
from app.knowledge_base.metadata import KNOWLEDGE_RESULT_VERSION, KnowledgeMetadata
from app.knowledge_base.models import (
    CategoryCount,
    CategoryReport,
    DifficultyCount,
    DifficultyLevel,
    KnowledgeCategory,
    KnowledgeConfiguration,
    KnowledgeEntry,
    KnowledgeResult,
    KnowledgeSearchQuery,
    KnowledgeStatistics,
    LearningProgress,
    TagCount,
    TopicReport,
)
from app.knowledge_base.registry import KnowledgeRegistry
from app.knowledge_base.report import KnowledgeReport
from app.knowledge_base.runner import BaseKnowledgeRunner, KnowledgeRunner, KnowledgeSession, SessionStatus
from app.knowledge_base.search import KnowledgeSearchEngine
from app.knowledge_base.serializer import KnowledgeSerializer
from app.knowledge_base.statistics import KnowledgeStatisticsEngine
from app.knowledge_base.validator import KnowledgeCheckResult, KnowledgeIssue, KnowledgeValidator

__all__ = [
    "KnowledgeBaseEngine",
    "KnowledgeRunner",
    "BaseKnowledgeRunner",
    "KnowledgeSession",
    "SessionStatus",
    "KnowledgeContext",
    "KnowledgeCompiler",
    "KnowledgeValidator",
    "KnowledgeCheckResult",
    "KnowledgeIssue",
    "KnowledgeSerializer",
    "KnowledgeRegistry",
    "KnowledgeReport",
    "KnowledgeMetadata",
    "KNOWLEDGE_RESULT_VERSION",
    "KnowledgeConfiguration",
    "KnowledgeResult",
    "KnowledgeEntry",
    "KnowledgeCategory",
    "DifficultyLevel",
    "KnowledgeSearchQuery",
    "KnowledgeSearchEngine",
    "KnowledgeStatisticsEngine",
    "KnowledgeStatistics",
    "CategoryCount",
    "DifficultyCount",
    "TagCount",
    "CategoryReport",
    "TopicReport",
    "LearningProgress",
    "KnowledgeBaseError",
    "KnowledgeConfigurationError",
    "KnowledgeValidationError",
    "KnowledgeExecutionError",
    "KnowledgeNotFoundError",
    "KnowledgeDisabledError",
    "KnowledgeRegistrationError",
]
