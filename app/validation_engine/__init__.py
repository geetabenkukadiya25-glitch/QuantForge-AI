"""Walk Forward & Monte Carlo Validation Engine.

Validates an already-chosen `app.optimization_engine` candidate. It MUST
NOT optimize (never re-invokes Optimization Engine's search methods) and
MUST NOT backtest independently (every statistic comes from a real,
unmodified `app.backtesting_engine.BacktestRunner` call, or from
resampling an already-produced trade list). It NEVER connects to a
broker and NEVER executes live trades.

Consumes ONLY the Optimization Engine, the Backtesting Engine, Strategy
Builder, the Historical Data Engine, the Indicator Engine, and the Smart
Money Engine -- never a broker API, never MT5.
"""

from app.validation_engine.analysis import ConfidenceAnalyzer, RobustnessAnalyzer, StabilityAnalyzer
from app.validation_engine.compiler import ValidationCompiler
from app.validation_engine.context import ValidationContext
from app.validation_engine.engine import ValidationEngine
from app.validation_engine.exceptions import (
    ValidationConfigurationError,
    ValidationDisabledError,
    ValidationEngineError,
    ValidationExecutionError,
    ValidationNotFoundError,
    ValidationRegistrationError,
    ValidationValidationError,
)
from app.validation_engine.metadata import VALIDATION_RESULT_VERSION, ValidationMetadata
from app.validation_engine.models import (
    ConfidenceScore,
    MonteCarloConfiguration,
    MonteCarloDistributionPoint,
    MonteCarloMethod,
    MonteCarloResult,
    RobustnessScore,
    StabilityScore,
    ValidationConfiguration,
    ValidationResult,
    WalkForwardConfiguration,
    WalkForwardResult,
    WalkForwardWindow,
    WalkForwardWindowOutcome,
    WindowStatus,
    WindowType,
)
from app.validation_engine.monte_carlo import MonteCarloEngine
from app.validation_engine.registry import ValidationRegistry
from app.validation_engine.report import ValidationReport
from app.validation_engine.resolve import ResolvedCandidate, resolve_candidate
from app.validation_engine.runner import BaseValidationRunner, SessionStatus, ValidationRunner, ValidationSession
from app.validation_engine.serializer import ValidationSerializer
from app.validation_engine.validator import ValidationCheckResult, ValidationIssue, ValidationValidator
from app.validation_engine.walk_forward import WalkForwardEngine

__all__ = [
    "ValidationEngine",
    "ValidationRunner",
    "BaseValidationRunner",
    "ValidationSession",
    "SessionStatus",
    "ValidationContext",
    "ValidationCompiler",
    "ValidationValidator",
    "ValidationCheckResult",
    "ValidationIssue",
    "ValidationSerializer",
    "ValidationRegistry",
    "ValidationReport",
    "ValidationMetadata",
    "VALIDATION_RESULT_VERSION",
    "ValidationConfiguration",
    "ValidationResult",
    "ResolvedCandidate",
    "resolve_candidate",
    "WalkForwardEngine",
    "WalkForwardConfiguration",
    "WalkForwardWindow",
    "WalkForwardWindowOutcome",
    "WalkForwardResult",
    "WindowType",
    "WindowStatus",
    "MonteCarloEngine",
    "MonteCarloConfiguration",
    "MonteCarloDistributionPoint",
    "MonteCarloResult",
    "MonteCarloMethod",
    "RobustnessAnalyzer",
    "ConfidenceAnalyzer",
    "StabilityAnalyzer",
    "RobustnessScore",
    "ConfidenceScore",
    "StabilityScore",
    "ValidationEngineError",
    "ValidationConfigurationError",
    "ValidationValidationError",
    "ValidationExecutionError",
    "ValidationNotFoundError",
    "ValidationDisabledError",
    "ValidationRegistrationError",
]
