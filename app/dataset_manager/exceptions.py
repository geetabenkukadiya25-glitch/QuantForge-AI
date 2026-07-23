"""Exception hierarchy for Dataset Manager (Phase 18.6).

All exceptions derive from `app.core.exceptions.QuantForgeError`, matching
every other module's convention. This module never raises `app.data_engine`
exceptions itself -- it reuses them (`CSVFormatError`) for load/parse
failures and only defines exceptions unique to registry *management*.
"""

from app.core.exceptions import QuantForgeError


class DatasetManagerError(QuantForgeError):
    """Base class for all Dataset Manager errors."""


class DatasetNotFoundError(DatasetManagerError):
    """Raised when a referenced dataset id does not exist in the registry."""


class DuplicateDatasetError(DatasetManagerError):
    """Raised when an operation would create a second record for content
    that already has one (see `DatasetManager`'s hash-based dedup)."""


class ProtectedDatasetError(DatasetManagerError):
    """Raised when an operation not permitted on a protected dataset is
    attempted (delete, archive) -- use `set_protected(id, False)` first."""
