"""Exception hierarchy for the Professional Portfolio Management Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except PortfolioValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.portfolio_engine.validator import PortfolioIssue


class PortfolioEngineError(QuantForgeError):
    """Base class for all Portfolio Management Engine errors."""


class PortfolioConfigurationError(PortfolioEngineError):
    """Raised for an invalid `PortfolioConfiguration`."""


class PortfolioValidationError(PortfolioEngineError):
    """Raised when a portfolio context fails pre-execution validation.

    Carries the full list of `PortfolioIssue`s for a complete report.
    """

    def __init__(self, issues: list["PortfolioIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Portfolio context failed validation: {summary}")


class PortfolioExecutionError(PortfolioEngineError):
    """Raised for an internal integrity failure while compiling a portfolio."""


class PortfolioNotFoundError(PortfolioEngineError):
    """Raised when a requested portfolio result id isn't registered."""


class PortfolioDisabledError(PortfolioEngineError):
    """Raised when a requested portfolio result is registered but disabled."""


class PortfolioRegistrationError(PortfolioEngineError):
    """Raised for duplicate or malformed portfolio result registration."""
