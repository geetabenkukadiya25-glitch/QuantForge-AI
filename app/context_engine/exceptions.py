"""Exception hierarchy for the Market Context Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except ContextValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.context_engine.validator import ValidationIssue


class ContextEngineError(QuantForgeError):
    """Base class for all Market Context Engine errors."""


class ContextBuildError(ContextEngineError):
    """Raised when a `ContextSnapshot` cannot be built from the given inputs."""


class ContextValidationError(ContextEngineError):
    """Raised when a context snapshot fails validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Market context failed validation: {summary}")


class ContextVersionError(ContextEngineError):
    """Raised for unsupported or incompatible context schema versions."""


class ContextRegistryError(ContextEngineError):
    """Raised for context snapshot storage failures (not found, already exists, ...)."""
