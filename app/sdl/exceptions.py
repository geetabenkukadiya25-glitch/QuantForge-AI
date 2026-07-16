"""Exception hierarchy for the Strategy Definition Language (SDL).

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly or narrowly (e.g. `except SDLValidationError`).
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.sdl.validator import ValidationIssue


class SDLError(QuantForgeError):
    """Base class for all SDL errors."""


class SDLParseError(SDLError):
    """Raised when raw text cannot be parsed into an SDL document."""


class SDLValidationError(SDLError):
    """Raised when a strategy document fails validation.

    Carries the full list of `ValidationIssue`s so callers can present a
    complete, human-readable report instead of a single message.
    """

    def __init__(self, issues: list["ValidationIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Strategy definition failed validation: {summary}")


class SDLVersionError(SDLError):
    """Raised for unsupported or incompatible SDL/strategy versions."""


class SDLCompileError(SDLError):
    """Raised when a validated strategy cannot be compiled into an internal model."""


class SDLRegistryError(SDLError):
    """Raised for strategy registry storage failures (not found, already exists, ...)."""
