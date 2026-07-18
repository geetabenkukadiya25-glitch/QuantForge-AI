"""Professional Portfolio Management Engine.

An institutional portfolio management system that consumes
already-completed strategy results and manages them as a combined
portfolio. It is NOT an AI model. Consumes ONLY completed outputs from
Strategy Builder and the Backtesting Engine (both required), plus
optionally the Optimization Engine, Validation Engine, Replay Engine, and
Research Engine -- it never rebuilds any of them. It NEVER trades, NEVER
connects to a broker or MT5, NEVER places an order, NEVER optimizes, and
NEVER validates. Only aggregation and analysis.

Built additively as an approved-but-unplanned module, exactly like the
Research & Strategy Intelligence Engine before it -- `PROJECT_VISION.md`'s
locked roadmap numbering is unchanged (Phase 15 there remains "AI
Research Assistant"); see `docs/ROADMAP.md` for the conflict/resolution
record.
"""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.analytics import AnalyticsEngine
from app.portfolio_engine.compiler import PortfolioCompiler
from app.portfolio_engine.context import PortfolioContext, PortfolioStrategyEntry
from app.portfolio_engine.correlation import CorrelationEngine
from app.portfolio_engine.engine import PortfolioManagementEngine
from app.portfolio_engine.exceptions import (
    PortfolioConfigurationError,
    PortfolioDisabledError,
    PortfolioEngineError,
    PortfolioExecutionError,
    PortfolioNotFoundError,
    PortfolioRegistrationError,
    PortfolioValidationError,
)
from app.portfolio_engine.metadata import PORTFOLIO_RESULT_VERSION, PortfolioMetadata
from app.portfolio_engine.models import (
    AllocationBreakdown,
    AllocationBucket,
    AllocationMethod,
    CorrelationMatrix,
    CorrelationPair,
    ExposureEntry,
    ExposureReport,
    ManualWeight,
    PortfolioAnalytics,
    PortfolioConfiguration,
    PortfolioExecutiveSummary,
    PortfolioRanking,
    PortfolioResult,
    PortfolioStatistics,
    RankingCategory,
    RankingHighlight,
    StrategyAllocation,
)
from app.portfolio_engine.ranking import RankingEngine
from app.portfolio_engine.registry import PortfolioRegistry
from app.portfolio_engine.report import PortfolioReport
from app.portfolio_engine.risk import RiskEngine
from app.portfolio_engine.runner import BasePortfolioRunner, PortfolioRunner, PortfolioSession, SessionStatus
from app.portfolio_engine.serializer import PortfolioSerializer
from app.portfolio_engine.statistics import PortfolioStatisticsEngine
from app.portfolio_engine.validator import PortfolioCheckResult, PortfolioIssue, PortfolioValidator

__all__ = [
    "PortfolioManagementEngine",
    "PortfolioRunner",
    "BasePortfolioRunner",
    "PortfolioSession",
    "SessionStatus",
    "PortfolioContext",
    "PortfolioStrategyEntry",
    "PortfolioCompiler",
    "PortfolioValidator",
    "PortfolioCheckResult",
    "PortfolioIssue",
    "PortfolioSerializer",
    "PortfolioRegistry",
    "PortfolioReport",
    "PortfolioMetadata",
    "PORTFOLIO_RESULT_VERSION",
    "PortfolioConfiguration",
    "PortfolioResult",
    "AllocationEngine",
    "AllocationMethod",
    "ManualWeight",
    "StrategyAllocation",
    "AllocationBucket",
    "AllocationBreakdown",
    "CorrelationEngine",
    "CorrelationPair",
    "CorrelationMatrix",
    "ExposureEntry",
    "ExposureReport",
    "RiskEngine",
    "PortfolioStatisticsEngine",
    "PortfolioStatistics",
    "RankingEngine",
    "RankingCategory",
    "RankingHighlight",
    "PortfolioRanking",
    "AnalyticsEngine",
    "PortfolioAnalytics",
    "PortfolioExecutiveSummary",
    "PortfolioEngineError",
    "PortfolioConfigurationError",
    "PortfolioValidationError",
    "PortfolioExecutionError",
    "PortfolioNotFoundError",
    "PortfolioDisabledError",
    "PortfolioRegistrationError",
]
