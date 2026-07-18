"""Indicator Engine.

Calculates technical indicators over standardized OHLCV data. This
engine is responsible ONLY for calculation -- it never generates
buy/sell signals, never contains strategy logic, and never executes
trades. Indicators are reusable calculation components consumed by
future engines (Strategy Builder, Backtesting Engine, ...), never the
other way around.

This is the Single Source of Truth for "Indicators" per
`PROJECT_VISION.md`.
"""

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.exceptions import (
    IndicatorConfigurationError,
    IndicatorDisabledError,
    IndicatorEngineError,
    IndicatorExecutionError,
    IndicatorNotFoundError,
    IndicatorRegistrationError,
    IndicatorValidationError,
)
from app.indicator_engine.factory import IndicatorFactory
from app.indicator_engine.indicators import ALL_INDICATORS
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec
from app.indicator_engine.registry import IndicatorRegistry
from app.indicator_engine.result import IndicatorResult
from app.indicator_engine.serializer import IndicatorSerializer
from app.indicator_engine.validator import IndicatorValidator, ValidationIssue, ValidationResult

__all__ = [
    "IndicatorEngine",
    "IndicatorRegistry",
    "IndicatorFactory",
    "IndicatorContext",
    "IndicatorValidator",
    "ValidationResult",
    "ValidationIssue",
    "IndicatorSerializer",
    "IndicatorResult",
    "IndicatorMetadata",
    "ParameterSpec",
    "BaseIndicator",
    "ALL_INDICATORS",
    "IndicatorEngineError",
    "IndicatorConfigurationError",
    "IndicatorExecutionError",
    "IndicatorNotFoundError",
    "IndicatorDisabledError",
    "IndicatorValidationError",
    "IndicatorRegistrationError",
]
