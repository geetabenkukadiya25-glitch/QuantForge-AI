"""Optimization Engine.

Optimizes `app.strategy_builder.StrategyModel` parameters using the
existing, unmodified Backtesting Engine -- Grid Search and Random Search
only (framework only; future algorithms will be added later). It NEVER
executes live trades, NEVER connects to a broker, and NEVER modifies
Strategy Builder logic.

Consumes ONLY Strategy Builder's output (`StrategyModel`), the
Backtesting Engine, the Historical Data Engine, the Indicator Engine, and
the Smart Money Engine -- never a broker API, never MT5.
"""

from app.optimization_engine.compiler import OptimizationCompiler
from app.optimization_engine.context import OptimizationContext
from app.optimization_engine.engine import OptimizationEngine
from app.optimization_engine.exceptions import (
    OptimizationConfigurationError,
    OptimizationDisabledError,
    OptimizationEngineError,
    OptimizationExecutionError,
    OptimizationNotFoundError,
    OptimizationRegistrationError,
    OptimizationValidationError,
)
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION, OptimizationMetadata
from app.optimization_engine.models import (
    Objective,
    OptimizationCandidate,
    OptimizationCandidateOutcome,
    OptimizationConfiguration,
    OptimizationHistory,
    OptimizationResult,
    OptimizationStatistics,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.optimization_engine.registry import OptimizationRegistry
from app.optimization_engine.report import OptimizationReport
from app.optimization_engine.runner import BaseOptimizationRunner, OptimizationRunner, OptimizationSession, SessionStatus
from app.optimization_engine.search import BaseOptimizer, GridSearchOptimizer, RandomSearchOptimizer
from app.optimization_engine.serializer import OptimizationSerializer
from app.optimization_engine.validator import OptimizationValidator, ValidationIssue, ValidationResult

__all__ = [
    "OptimizationEngine",
    "OptimizationRunner",
    "BaseOptimizationRunner",
    "OptimizationSession",
    "SessionStatus",
    "OptimizationContext",
    "OptimizationCompiler",
    "OptimizationValidator",
    "ValidationResult",
    "ValidationIssue",
    "OptimizationSerializer",
    "OptimizationRegistry",
    "OptimizationReport",
    "OptimizationMetadata",
    "OPTIMIZATION_RESULT_VERSION",
    "OptimizationConfiguration",
    "OptimizationResult",
    "ParameterSpace",
    "ParameterDefinition",
    "ParameterKind",
    "ParameterTarget",
    "ParameterGenerator",
    "OptimizationCandidate",
    "OptimizationCandidateOutcome",
    "OptimizationHistory",
    "OptimizationStatistics",
    "Objective",
    "SearchMethod",
    "BaseOptimizer",
    "GridSearchOptimizer",
    "RandomSearchOptimizer",
    "OptimizationEngineError",
    "OptimizationConfigurationError",
    "OptimizationValidationError",
    "OptimizationExecutionError",
    "OptimizationNotFoundError",
    "OptimizationDisabledError",
    "OptimizationRegistrationError",
]
