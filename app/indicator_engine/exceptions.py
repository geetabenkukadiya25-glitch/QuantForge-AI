"""Exception hierarchy for the Indicator Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except IndicatorValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.indicator_engine.validator import ValidationIssue


class IndicatorEngineError(QuantForgeError):
    """Base class for all Indicator Engine errors."""


class IndicatorConfigurationError(IndicatorEngineError):
    """Raised for an invalid indicator configuration."""


class IndicatorExecutionError(IndicatorEngineError):
    """Raised for an internal integrity failure while computing an indicator."""


class IndicatorNotFoundError(IndicatorEngineError):
    """Raised when a requested indicator name isn't registered."""


class IndicatorDisabledError(IndicatorEngineError):
    """Raised when a requested indicator is registered but disabled."""


class IndicatorValidationError(IndicatorEngineError):
    """Raised when parameters, input, or output fail validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Indicator failed validation: {summary}")


class IndicatorRegistrationError(IndicatorEngineError):
    """Raised for duplicate or malformed indicator registration."""
