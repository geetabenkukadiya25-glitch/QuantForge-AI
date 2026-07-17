"""Exception hierarchy for the Replay Engine.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except ReplayValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.replay_engine.validator import ReplayIssue


class ReplayEngineError(QuantForgeError):
    """Base class for all Replay Engine errors."""


class ReplayConfigurationError(ReplayEngineError):
    """Raised for an invalid `ReplayConfiguration`."""


class ReplayValidationError(ReplayEngineError):
    """Raised when a replay context fails pre-execution validation.

    Carries the full list of `ReplayIssue`s for a complete report.
    """

    def __init__(self, issues: list["ReplayIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Replay context failed validation: {summary}")


class ReplayExecutionError(ReplayEngineError):
    """Raised for an internal integrity failure while preparing a replay."""


class ReplayNavigationError(ReplayEngineError):
    """Raised for an invalid timeline navigation or playback-state transition
    (e.g. jumping out of range, pausing a replay that isn't playing)."""


class ReplayNotFoundError(ReplayEngineError):
    """Raised when a requested replay result id isn't registered."""


class ReplayDisabledError(ReplayEngineError):
    """Raised when a requested replay result is registered but disabled."""


class ReplayRegistrationError(ReplayEngineError):
    """Raised for duplicate or malformed replay result registration."""
