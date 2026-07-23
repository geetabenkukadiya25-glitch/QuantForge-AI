"""Exception hierarchy for Data Catalog (Phase 17.5).

Mirrors `app.dataset_manager.exceptions` -- derives from the same
project-wide `QuantForgeError`. The catalog is a read-only/observer layer
over `DatasetManager`, so it re-raises `DatasetNotFoundError` from there
rather than defining its own "not found" exception.
"""

from app.core.exceptions import QuantForgeError


class DataCatalogError(QuantForgeError):
    """Base class for all Data Catalog errors."""
