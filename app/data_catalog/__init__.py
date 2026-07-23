"""Data Catalog (Phase 17.5) -- a read-only governance layer on top of
Dataset Manager (Phase 18.6): lineage, a dependency tree, usage
analytics, catalog-wide search/filters, and its own audit trail.

Pure observability layer, mirroring `app.dataset_manager`'s architecture
a third time: nothing here duplicates or modifies `DatasetManager`,
`JobManager`, or `StrategyLibraryManager` state -- it only reads them and
persists its own small overlay (owner/notes) plus a usage-context log
used to correlate jobs to datasets.
"""

from app.data_catalog.catalog import DataCatalog
from app.data_catalog.exceptions import DataCatalogError
from app.data_catalog.models import (
    CatalogAuditEvent,
    CatalogAuditEventType,
    CatalogOverlay,
    CatalogRecord,
    DatasetDependencyNode,
    DatasetLineageEvent,
    DatasetUsageContext,
    DatasetUsageStats,
    LineageEventKind,
)

__all__ = [
    "DataCatalog",
    "DataCatalogError",
    "CatalogAuditEvent",
    "CatalogAuditEventType",
    "CatalogOverlay",
    "CatalogRecord",
    "DatasetDependencyNode",
    "DatasetLineageEvent",
    "DatasetUsageContext",
    "DatasetUsageStats",
    "LineageEventKind",
]
