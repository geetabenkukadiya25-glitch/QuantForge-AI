"""Strategy Builder.

Combines SDL, Market Context, Indicator, and Smart Money Engine outputs
into a reusable executable `StrategyModel`. It does NOT execute trades,
place orders, backtest, optimize parameters, or generate AI decisions --
it only builds and validates executable strategy definitions.

Consumes ONLY the SDL Engine, Market Context Engine, Indicator Engine,
and Smart Money Engine -- never execution logic, never broker APIs.
"""

from app.strategy_builder.builder import BaseStrategyBuilder, StrategyBuilder
from app.strategy_builder.compiler import StrategyCompiler
from app.strategy_builder.context import StrategyContext
from app.strategy_builder.exceptions import (
    StrategyBuilderError,
    StrategyDisabledError,
    StrategyNotFoundError,
    StrategyRegistrationError,
    StrategyValidationError,
)
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION, StrategyMetadata
from app.strategy_builder.models import (
    ContextRequirement,
    DependencyEdge,
    DependencyGraph,
    DetectorReference,
    ExecutionPipeline,
    ExecutionStep,
    IndicatorReference,
    RuleReference,
    StrategyModel,
)
from app.strategy_builder.registry import StrategyRegistry
from app.strategy_builder.resolution import ResolvedComponents, resolve_components
from app.strategy_builder.result import StrategyResult
from app.strategy_builder.serializer import StrategySerializer
from app.strategy_builder.validator import StrategyValidator, ValidationIssue, ValidationResult

__all__ = [
    "StrategyBuilder",
    "BaseStrategyBuilder",
    "StrategyContext",
    "StrategyCompiler",
    "StrategyValidator",
    "ValidationResult",
    "ValidationIssue",
    "StrategyRegistry",
    "StrategySerializer",
    "StrategyMetadata",
    "STRATEGY_MODEL_VERSION",
    "StrategyModel",
    "StrategyResult",
    "IndicatorReference",
    "DetectorReference",
    "RuleReference",
    "ContextRequirement",
    "DependencyEdge",
    "DependencyGraph",
    "ExecutionStep",
    "ExecutionPipeline",
    "ResolvedComponents",
    "resolve_components",
    "StrategyBuilderError",
    "StrategyNotFoundError",
    "StrategyDisabledError",
    "StrategyValidationError",
    "StrategyRegistrationError",
]
