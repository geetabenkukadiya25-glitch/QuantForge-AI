"""Strategy Definition Language (SDL).

A strategy in QuantForge AI is a machine-readable document -- not Python
code, not MQL5 -- represented by `StrategyDefinition`. Every future
engine (Indicator Engine, Strategy Builder, Backtesting Engine,
Optimization Engine, Replay Engine, EA Generator, ...) must consume this
same SDL rather than hardcoding its own strategy representation (the
Single Source of Truth rule in `PROJECT_VISION.md`).

This module contains infrastructure only: no indicators, no strategy
execution, no backtesting, no optimization, no AI, per the Phase 4 scope.
"""

from app.sdl.compiler import CompiledStrategy, StrategyCompiler
from app.sdl.exceptions import (
    SDLCompileError,
    SDLConfigurationError,
    SDLError,
    SDLExecutionError,
    SDLParseError,
    SDLRegistryError,
    SDLValidationError,
    SDLVersionError,
)
from app.sdl.models import (
    Alerts,
    Bias,
    BreakEvenRule,
    ExecutionRules,
    IndicatorSpec,
    Market,
    Metadata,
    NewsRules,
    PartialCloseRule,
    PositionSizing,
    RiskManagement,
    Rule,
    SDL_SECTIONS,
    ScoringCriterion,
    SpreadRules,
    StopLossRule,
    StrategyDefinition,
    TakeProfitRule,
    TimeRules,
    TradeManagement,
    TrailingStopRule,
)
from app.sdl.parser import StrategyParser
from app.sdl.registry import StrategyRegistry, StrategySummary
from app.sdl.schema_manager import SchemaManager
from app.sdl.serializer import StrategySerializer
from app.sdl.validator import StrategyValidator, ValidationIssue, ValidationResult
from app.sdl.version import SDL_VERSION, SUPPORTED_SDL_VERSIONS, VersionManager

__all__ = [
    # Root document + sections
    "StrategyDefinition",
    "Metadata",
    "Market",
    "Bias",
    "Rule",
    "IndicatorSpec",
    "RiskManagement",
    "PositionSizing",
    "TradeManagement",
    "StopLossRule",
    "TakeProfitRule",
    "TrailingStopRule",
    "BreakEvenRule",
    "PartialCloseRule",
    "NewsRules",
    "SpreadRules",
    "TimeRules",
    "ExecutionRules",
    "ScoringCriterion",
    "Alerts",
    "SDL_SECTIONS",
    # Core services
    "StrategyParser",
    "StrategyValidator",
    "ValidationResult",
    "ValidationIssue",
    "StrategySerializer",
    "StrategyCompiler",
    "CompiledStrategy",
    "StrategyRegistry",
    "StrategySummary",
    "SchemaManager",
    "VersionManager",
    "SDL_VERSION",
    "SUPPORTED_SDL_VERSIONS",
    # Exceptions
    "SDLError",
    "SDLConfigurationError",
    "SDLExecutionError",
    "SDLParseError",
    "SDLValidationError",
    "SDLVersionError",
    "SDLCompileError",
    "SDLRegistryError",
]
