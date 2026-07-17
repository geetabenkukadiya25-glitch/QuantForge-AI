"""Exception hierarchy for the Walk Forward & Monte Carlo Validation Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except ValidationValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.validation_engine.validator import ValidationIssue


class ValidationEngineError(QuantForgeError):
    """Base class for all Validation Engine errors."""


class ValidationConfigurationError(ValidationEngineError):
    """Raised for an invalid `ValidationConfiguration`, `WalkForwardConfiguration`, or `MonteCarloConfiguration`."""


class ValidationValidationError(ValidationEngineError):
    """Raised when a validation run fails pre-execution validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Validation run failed validation: {summary}")


class ValidationExecutionError(ValidationEngineError):
    """Raised for an internal integrity failure (defensive) -- e.g. a reconstructed
    candidate StrategyModel whose checksum doesn't match the Optimization Engine's record."""


class ValidationNotFoundError(ValidationEngineError):
    """Raised when a requested validation result id isn't registered."""


class ValidationDisabledError(ValidationEngineError):
    """Raised when a requested validation result is registered but disabled."""


class ValidationRegistrationError(ValidationEngineError):
    """Raised for duplicate or malformed validation result registration."""
