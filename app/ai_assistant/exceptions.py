"""Exception hierarchy for the AI Research Assistant.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except AssistantValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.ai_assistant.validator import AssistantIssue


class AssistantEngineError(QuantForgeError):
    """Base class for all AI Research Assistant errors."""


class AssistantConfigurationError(AssistantEngineError):
    """Raised for an invalid `AssistantConfiguration`."""


class AssistantValidationError(AssistantEngineError):
    """Raised when an assistant context fails pre-execution validation.

    Carries the full list of `AssistantIssue`s for a complete report.
    """

    def __init__(self, issues: list["AssistantIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Assistant context failed validation: {summary}")


class AssistantExecutionError(AssistantEngineError):
    """Raised for an internal integrity failure while answering a query."""


class AssistantNotFoundError(AssistantEngineError):
    """Raised when a requested assistant result id isn't registered."""


class AssistantDisabledError(AssistantEngineError):
    """Raised when a requested assistant result is registered but disabled."""


class AssistantRegistrationError(AssistantEngineError):
    """Raised for duplicate or malformed assistant result registration."""
