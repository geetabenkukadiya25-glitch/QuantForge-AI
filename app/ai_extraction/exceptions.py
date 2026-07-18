"""Exception hierarchy for the AI Strategy Extraction Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except ExtractionValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.ai_extraction.validator import ExtractionIssue


class ExtractionEngineError(QuantForgeError):
    """Base class for all AI Strategy Extraction Engine errors."""


class ExtractionConfigurationError(ExtractionEngineError):
    """Raised for an invalid `ExtractionConfiguration`."""


class ExtractionValidationError(ExtractionEngineError):
    """Raised when an extraction context fails pre-execution validation.

    Carries the full list of `ExtractionIssue`s for a complete report.
    """

    def __init__(self, issues: list["ExtractionIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Extraction context failed validation: {summary}")


class ExtractionExecutionError(ExtractionEngineError):
    """Raised for an internal integrity failure while compiling an extraction."""


class ExtractionNotFoundError(ExtractionEngineError):
    """Raised when a requested extraction result id isn't registered."""


class ExtractionDisabledError(ExtractionEngineError):
    """Raised when a requested extraction result is registered but disabled."""


class ExtractionRegistrationError(ExtractionEngineError):
    """Raised for duplicate or malformed extraction result registration."""
