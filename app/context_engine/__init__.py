"""Market Context Engine.

Produces standardized, immutable `ContextSnapshot`s describing the
current market state (symbol, timeframe, session, time, and reserved
market-state placeholders). This engine **never generates buy/sell
signals** -- per `PROJECT_VISION.md`'s "Context Before Decision"
principle, every future decision engine must consume a `ContextSnapshot`
rather than touching raw market data directly.

This module contains no indicators, no strategy logic, no AI, no
backtesting, no optimization, no replay, and no execution, per the
Phase 5 scope.
"""

from app.context_engine.builder import MARKET_STATE_PLACEHOLDERS_FLAG, ContextBuilder
from app.context_engine.context_engine import MarketContextEngine
from app.context_engine.exceptions import (
    ContextBuildError,
    ContextConfigurationError,
    ContextEngineError,
    ContextExecutionError,
    ContextRegistryError,
    ContextValidationError,
    ContextVersionError,
)
from app.context_engine.models import (
    ContextSnapshot,
    MarketContext,
    MarketStatePlaceholders,
    SessionContext,
    SymbolContext,
    TimeContext,
    TimeframeContext,
)
from app.context_engine.registry import ContextRegistry, ContextSummary
from app.context_engine.serializer import ContextSerializer
from app.context_engine.validator import ContextValidator, ValidationIssue, ValidationResult
from app.context_engine.version import CONTEXT_VERSION, ContextVersionManager

__all__ = [
    # Root snapshot + sections
    "ContextSnapshot",
    "MarketContext",
    "TimeContext",
    "SessionContext",
    "SymbolContext",
    "TimeframeContext",
    "MarketStatePlaceholders",
    # Core services
    "MarketContextEngine",
    "ContextBuilder",
    "MARKET_STATE_PLACEHOLDERS_FLAG",
    "ContextValidator",
    "ValidationResult",
    "ValidationIssue",
    "ContextSerializer",
    "ContextRegistry",
    "ContextSummary",
    "ContextVersionManager",
    "CONTEXT_VERSION",
    # Exceptions
    "ContextEngineError",
    "ContextConfigurationError",
    "ContextExecutionError",
    "ContextBuildError",
    "ContextValidationError",
    "ContextVersionError",
    "ContextRegistryError",
]
