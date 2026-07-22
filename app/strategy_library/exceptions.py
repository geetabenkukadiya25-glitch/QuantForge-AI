"""Exception hierarchy for Strategy Library management (Phase 18).

All exceptions derive from `app.core.exceptions.QuantForgeError`, matching
every other module's convention. This module never raises `app.sdl`
exceptions itself -- it reuses them (`SDLParseError`, `SDLValidationError`)
for parsing/validation failures and only defines exceptions for concerns
unique to library *management* (protection, naming collisions, lookup).
"""

from app.core.exceptions import QuantForgeError


class StrategyLibraryError(QuantForgeError):
    """Base class for all Strategy Library management errors."""


class ProtectedStrategyError(StrategyLibraryError):
    """Raised when an operation not permitted on a built-in example is attempted.

    Built-in examples (`app/sdl/examples/`) may be opened, edited in the
    editor, validated, compiled, and exported -- but never overwritten,
    deleted, or renamed in place. Use `StrategyLibraryManager.save_as`
    instead.
    """


class StrategyFileNotFoundError(StrategyLibraryError):
    """Raised when a referenced strategy file does not exist in the library."""


class DuplicateFilenameError(StrategyLibraryError):
    """Raised when saving/renaming would overwrite an existing file without `overwrite=True`."""


class VersionNotFoundError(StrategyLibraryError):
    """Raised when a requested version-history entry does not exist."""
