"""Exception hierarchy for the Research & Strategy Intelligence Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except ResearchValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.research_engine.validator import ResearchIssue


class ResearchEngineError(QuantForgeError):
    """Base class for all Research Engine errors."""


class ResearchConfigurationError(ResearchEngineError):
    """Raised for an invalid `ResearchConfiguration`."""


class ResearchValidationError(ResearchEngineError):
    """Raised when a research context fails pre-execution validation.

    Carries the full list of `ResearchIssue`s for a complete report.
    """

    def __init__(self, issues: list["ResearchIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Research context failed validation: {summary}")


class ResearchExecutionError(ResearchEngineError):
    """Raised for an internal integrity failure while compiling research."""


class ResearchNotFoundError(ResearchEngineError):
    """Raised when a requested research result id isn't registered."""


class ResearchDisabledError(ResearchEngineError):
    """Raised when a requested research result is registered but disabled."""


class ResearchRegistrationError(ResearchEngineError):
    """Raised for duplicate or malformed research result registration."""
