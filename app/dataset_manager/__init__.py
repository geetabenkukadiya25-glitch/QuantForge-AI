"""Dataset Manager (Phase 18.6) -- a centralized registry that turns every
imported historical dataset into a persistent, managed asset: import with
content-hash dedup, search/filter, favorites/tags/archive, versioning,
audit log, validation/health scoring, and export.

Pure orchestration + file-management layer, mirroring
`app.strategy_library`'s architecture: nothing here reimplements CSV
parsing/cleaning/validation/export (always delegates to
`app.data_engine`), and nothing here touches any trading/strategy/
backtesting/AI/MT5 engine.
"""

from app.dataset_manager.dataset_manager import DatasetManager
from app.dataset_manager.exceptions import (
    DatasetManagerError,
    DatasetNotFoundError,
    DuplicateDatasetError,
    ProtectedDatasetError,
)
from app.dataset_manager.models import (
    STANDARD_TAGS,
    ColumnInfo,
    DatasetAuditEvent,
    DatasetAuditEventType,
    DatasetHealth,
    DatasetPreview,
    DatasetRecord,
    DatasetSource,
    DatasetStatistics,
    DatasetVersion,
    DatasetVersionEventType,
    HealthCheck,
)

__all__ = [
    "DatasetManager",
    "DatasetManagerError",
    "DatasetNotFoundError",
    "DuplicateDatasetError",
    "ProtectedDatasetError",
    "STANDARD_TAGS",
    "ColumnInfo",
    "DatasetAuditEvent",
    "DatasetAuditEventType",
    "DatasetHealth",
    "DatasetPreview",
    "DatasetRecord",
    "DatasetSource",
    "DatasetStatistics",
    "DatasetVersion",
    "DatasetVersionEventType",
    "HealthCheck",
]
