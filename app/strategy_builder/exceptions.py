"""Exception hierarchy for the Strategy Builder.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except StrategyValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.strategy_builder.validator import ValidationIssue


class StrategyBuilderError(QuantForgeError):
    """Base class for all Strategy Builder errors."""


class StrategyConfigurationError(StrategyBuilderError):
    """Raised for an invalid strategy build configuration."""


class StrategyExecutionError(StrategyBuilderError):
    """Raised for an internal integrity failure while compiling a strategy."""


class StrategyNotFoundError(StrategyBuilderError):
    """Raised when a requested strategy id isn't registered."""


class StrategyDisabledError(StrategyBuilderError):
    """Raised when a requested strategy is registered but disabled."""


class StrategyValidationError(StrategyBuilderError):
    """Raised when a strategy fails dependency resolution or validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Strategy failed validation: {summary}")


class StrategyRegistrationError(StrategyBuilderError):
    """Raised for duplicate or malformed strategy registration."""
