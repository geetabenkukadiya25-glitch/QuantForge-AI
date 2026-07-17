"""Exception hierarchy for the Knowledge Base Platform.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except KnowledgeValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.knowledge_base.validator import KnowledgeIssue


class KnowledgeBaseError(QuantForgeError):
    """Base class for all Knowledge Base errors."""


class KnowledgeConfigurationError(KnowledgeBaseError):
    """Raised for an invalid `KnowledgeConfiguration`."""


class KnowledgeValidationError(KnowledgeBaseError):
    """Raised when a knowledge context fails pre-execution validation.

    Carries the full list of `KnowledgeIssue`s for a complete report.
    """

    def __init__(self, issues: list["KnowledgeIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Knowledge context failed validation: {summary}")


class KnowledgeExecutionError(KnowledgeBaseError):
    """Raised for an internal integrity failure while compiling the knowledge base."""


class KnowledgeNotFoundError(KnowledgeBaseError):
    """Raised when a requested knowledge result or entry id isn't registered."""


class KnowledgeDisabledError(KnowledgeBaseError):
    """Raised when a requested knowledge result is registered but disabled."""


class KnowledgeRegistrationError(KnowledgeBaseError):
    """Raised for duplicate or malformed knowledge result registration."""
