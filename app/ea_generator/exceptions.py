"""Exception hierarchy for the Professional EA Generator Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except EAValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.ea_generator.validator import EAGeneratorIssue


class EAGeneratorEngineError(QuantForgeError):
    """Base class for all EA Generator Engine errors."""


class EAConfigurationError(EAGeneratorEngineError):
    """Raised for an invalid `EAGeneratorConfiguration`."""


class EAValidationError(EAGeneratorEngineError):
    """Raised when an EA generation context fails pre-execution validation.

    Carries the full list of `EAGeneratorIssue`s for a complete report.
    """

    def __init__(self, issues: list["EAGeneratorIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"EA generation context failed validation: {summary}")


class EAExecutionError(EAGeneratorEngineError):
    """Raised for an internal integrity failure while generating an EA."""


class EANotFoundError(EAGeneratorEngineError):
    """Raised when a requested EA generation result id isn't registered."""


class EADisabledError(EAGeneratorEngineError):
    """Raised when a requested EA generation result is registered but disabled."""


class EARegistrationError(EAGeneratorEngineError):
    """Raised for duplicate or malformed EA generation result registration."""
