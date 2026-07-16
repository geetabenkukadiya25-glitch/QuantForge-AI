"""Exception hierarchy for the Smart Money Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except SMCValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.smart_money_engine.validator import ValidationIssue


class SMCEngineError(QuantForgeError):
    """Base class for all Smart Money Engine errors."""


class SMCDetectorNotFoundError(SMCEngineError):
    """Raised when a requested detector name isn't registered."""


class SMCDetectorDisabledError(SMCEngineError):
    """Raised when a requested detector is registered but disabled."""


class SMCValidationError(SMCEngineError):
    """Raised when parameters, input, or output fail validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Detector failed validation: {summary}")


class SMCRegistrationError(SMCEngineError):
    """Raised for duplicate or malformed detector registration."""
