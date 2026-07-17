"""Research & Strategy Intelligence Engine.

An institutional research system that consumes already-completed
research results and produces professional analysis. It is NOT an AI
model. Consumes ONLY completed outputs from Strategy Builder,
Backtesting Engine, Optimization Engine, Validation Engine, and
(optionally, for visualization only) Replay Engine -- it never rebuilds
any of them. It NEVER executes trades, NEVER optimizes strategies,
NEVER replays charts, and NEVER connects to a broker or MT5.
"""

from app.research_engine.analytics import AnalyticsEngine
from app.research_engine.comparison import ComparisonEngine
from app.research_engine.compiler import ResearchCompiler
from app.research_engine.context import ResearchContext, StrategyRecord
from app.research_engine.engine import ResearchEngine
from app.research_engine.exceptions import (
    ResearchConfigurationError,
    ResearchDisabledError,
    ResearchEngineError,
    ResearchExecutionError,
    ResearchNotFoundError,
    ResearchRegistrationError,
    ResearchValidationError,
)
from app.research_engine.insights import InsightsEngine
from app.research_engine.metadata import RESEARCH_RESULT_VERSION, ResearchMetadata
from app.research_engine.models import (
    ComparisonStatistics,
    ExecutiveSummary,
    InsightSeverity,
    InstitutionalQualityScore,
    MonteCarloRobustnessSummary,
    OptimizationHistorySummary,
    RankingEntry,
    RankingMetric,
    Recommendation,
    RecommendationPriority,
    ResearchAnalytics,
    ResearchConfidenceScore,
    ResearchConfiguration,
    ResearchResult,
    SessionPerformance,
    StrategyInsights,
    StrategyScore,
    SymbolPerformance,
    TimeframePerformance,
    UsageStat,
    WalkForwardStabilitySummary,
)
from app.research_engine.ranking import RankingEngine, ScoringEngine
from app.research_engine.recommendations import RecommendationEngine
from app.research_engine.registry import ResearchRegistry
from app.research_engine.report import ResearchReport
from app.research_engine.runner import BaseResearchRunner, ResearchRunner, ResearchSession, SessionStatus
from app.research_engine.serializer import ResearchSerializer
from app.research_engine.statistics import ResearchStatisticsEngine
from app.research_engine.validator import ResearchCheckResult, ResearchIssue, ResearchValidator

__all__ = [
    "ResearchEngine",
    "ResearchRunner",
    "BaseResearchRunner",
    "ResearchSession",
    "SessionStatus",
    "ResearchContext",
    "StrategyRecord",
    "ResearchCompiler",
    "ResearchValidator",
    "ResearchCheckResult",
    "ResearchIssue",
    "ResearchSerializer",
    "ResearchRegistry",
    "ResearchReport",
    "ResearchMetadata",
    "RESEARCH_RESULT_VERSION",
    "ResearchConfiguration",
    "ResearchResult",
    "ResearchStatisticsEngine",
    "ComparisonStatistics",
    "ComparisonEngine",
    "ScoringEngine",
    "RankingEngine",
    "RankingEntry",
    "RankingMetric",
    "StrategyScore",
    "ResearchConfidenceScore",
    "InstitutionalQualityScore",
    "AnalyticsEngine",
    "ResearchAnalytics",
    "UsageStat",
    "SymbolPerformance",
    "SessionPerformance",
    "TimeframePerformance",
    "OptimizationHistorySummary",
    "WalkForwardStabilitySummary",
    "MonteCarloRobustnessSummary",
    "InsightsEngine",
    "StrategyInsights",
    "InsightSeverity",
    "RecommendationEngine",
    "Recommendation",
    "RecommendationPriority",
    "ExecutiveSummary",
    "ResearchEngineError",
    "ResearchConfigurationError",
    "ResearchValidationError",
    "ResearchExecutionError",
    "ResearchNotFoundError",
    "ResearchDisabledError",
    "ResearchRegistrationError",
]
