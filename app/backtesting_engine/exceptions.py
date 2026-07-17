"""Exception hierarchy for the Backtesting Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except BacktestValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.backtesting_engine.validator import ValidationIssue


class BacktestingEngineError(QuantForgeError):
    """Base class for all Backtesting Engine errors."""


class BacktestConfigurationError(BacktestingEngineError):
    """Raised for an invalid `BacktestConfiguration`."""


class BacktestDataError(BacktestingEngineError):
    """Raised when historical data is incompatible with the requested backtest."""


class BacktestValidationError(BacktestingEngineError):
    """Raised when a backtest run fails pre-execution validation.

    Carries the full list of `ValidationIssue`s for a complete report.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Backtest failed validation: {summary}")


class BacktestExecutionError(BacktestingEngineError):
    """Raised for an internal simulation-integrity failure (defensive)."""


class BacktestNotFoundError(BacktestingEngineError):
    """Raised when a requested backtest result id isn't registered."""


class BacktestDisabledError(BacktestingEngineError):
    """Raised when a requested backtest result is registered but disabled."""


class BacktestRegistrationError(BacktestingEngineError):
    """Raised for duplicate or malformed backtest result registration."""
