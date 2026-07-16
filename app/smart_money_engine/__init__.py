"""Smart Money Engine.

Detects and describes Smart Money Concepts (SMC) structures over
standardized OHLCV data. This engine is responsible ONLY for detection
and description -- it never generates buy/sell signals, never contains
strategy logic, and never executes trades. Detectors are reusable
analysis components consumed by future engines (Strategy Builder,
Backtesting Engine, ...), never the other way around.
"""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors import ALL_DETECTORS
from app.smart_money_engine.engine import SmartMoneyEngine
from app.smart_money_engine.exceptions import (
    SMCDetectorDisabledError,
    SMCDetectorNotFoundError,
    SMCEngineError,
    SMCRegistrationError,
    SMCValidationError,
)
from app.smart_money_engine.factory import SMCFactory
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.registry import SMCRegistry
from app.smart_money_engine.result import SMCDetection, SMCResult
from app.smart_money_engine.serializer import SMCSerializer
from app.smart_money_engine.validator import SMCValidator, ValidationIssue, ValidationResult

__all__ = [
    "SmartMoneyEngine",
    "SMCRegistry",
    "SMCFactory",
    "SMCContext",
    "SMCValidator",
    "ValidationResult",
    "ValidationIssue",
    "SMCSerializer",
    "SMCResult",
    "SMCDetection",
    "SMCMetadata",
    "ParameterSpec",
    "BaseSMCDetector",
    "ALL_DETECTORS",
    "SMCEngineError",
    "SMCDetectorNotFoundError",
    "SMCDetectorDisabledError",
    "SMCValidationError",
    "SMCRegistrationError",
]
