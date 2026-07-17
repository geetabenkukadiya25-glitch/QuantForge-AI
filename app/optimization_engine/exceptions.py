"""Exception hierarchy for the Optimization Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except OptimizationValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.optimization_engine.validator import ValidationIssue


class OptimizationEngineError(QuantForgeError):
    """Base class for all Optimization Engine errors."""


class OptimizationConfigurationError(OptimizationEngineError):
    """Raised for an invalid `OptimizationConfiguration` or `ParameterSpace`."""


class OptimizationValidationError(OptimizationEngineError):
    """Raised when an optimization run fails pre-execution validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Optimization run failed validation: {summary}")


class OptimizationExecutionError(OptimizationEngineError):
    """Raised for an internal search/execution-integrity failure (defensive)."""


class OptimizationNotFoundError(OptimizationEngineError):
    """Raised when a requested optimization result id isn't registered."""


class OptimizationDisabledError(OptimizationEngineError):
    """Raised when a requested optimization result is registered but disabled."""


class OptimizationRegistrationError(OptimizationEngineError):
    """Raised for duplicate or malformed optimization result registration."""
