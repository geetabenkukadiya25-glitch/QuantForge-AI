"""Data classes/enums for Data Catalog (Phase 17.5). Pure data, no logic
beyond `to_dict`/`from_dict` -- mirrors `app.dataset_manager.models`
exactly. None of this duplicates a `DatasetRecord` field: every field
here is catalog-only metadata (owner, lineage, usage correlation) that
`DatasetManager` has no reason to know about.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LineageEventKind(str, Enum):
    """Exact events (read straight from `DatasetManager`'s own audit log /
    version history -- never re-derived) plus inferred "used by <job
    category>" events (built by `usage_tracker.sync_lineage`)."""

    IMPORTED = "IMPORTED"
    VALIDATED = "VALIDATED"
    REINDEXED = "REINDEXED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    DELETED = "DELETED"
    EXPORTED = "EXPORTED"
    USED_BY_BACKTEST = "USED_BY_BACKTEST"
    USED_BY_OPTIMIZATION = "USED_BY_OPTIMIZATION"
    USED_BY_VALIDATION = "USED_BY_VALIDATION"
    USED_BY_REPLAY = "USED_BY_REPLAY"
    USED_BY_RESEARCH = "USED_BY_RESEARCH"
    USED_BY_PORTFOLIO = "USED_BY_PORTFOLIO"
    USED_BY_STRATEGY = "USED_BY_STRATEGY"
    USED_BY_REPORTS = "USED_BY_REPORTS"
    USED_BY_OTHER = "USED_BY_OTHER"


@dataclass(frozen=True)
class DatasetLineageEvent:
    """One lineage entry for a dataset. `inferred=False` events are exact,
    read straight from `DatasetManager`'s audit log/version history.
    `inferred=True` events are best-effort correlations between the
    dataset-picker usage-context log and `JobManager` job history (see
    `usage_tracker.py`) -- always visibly labeled in the UI."""

    dataset_id: str
    kind: LineageEventKind
    timestamp: datetime
    inferred: bool
    job_id: str | None = None
    owner_page: str | None = None
    status: str | None = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp.isoformat(),
            "inferred": self.inferred,
            "job_id": self.job_id,
            "owner_page": self.owner_page,
            "status": self.status,
            "label": self.label,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DatasetLineageEvent":
        return DatasetLineageEvent(
            dataset_id=data["dataset_id"],
            kind=LineageEventKind(data["kind"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            inferred=data["inferred"],
            job_id=data.get("job_id"),
            owner_page=data.get("owner_page"),
            status=data.get("status"),
            label=data.get("label", ""),
        )


@dataclass(frozen=True)
class DatasetUsageContext:
    """One `(page_key, dataset_id, timestamp)` observation, written by the
    `dataset_picker` hook every time a dashboard resolves a managed
    dataset -- the raw signal `usage_tracker.sync_lineage` correlates
    against job history to infer "used by" lineage."""

    page_key: str
    dataset_id: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {"page_key": self.page_key, "dataset_id": self.dataset_id, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DatasetUsageContext":
        return DatasetUsageContext(
            page_key=data["page_key"],
            dataset_id=data["dataset_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass(frozen=True)
class DatasetUsageStats:
    """Phase 17.5 "Usage Analytics" -- aggregated from lineage events plus
    a live `JobManager` snapshot for the two "current" counters."""

    times_used: int
    last_used: datetime | None
    current_jobs: int
    completed_jobs: int
    strategies_referencing: int
    reports_generated: int
    validation_runs: int
    optimization_runs: int
    replay_runs: int
    average_runtime_seconds: float | None


@dataclass(frozen=True)
class DatasetDependencyNode:
    """One node in the collapsible dependency tree (Dataset -> Strategy ->
    Backtest -> Optimization -> Validation -> Replay -> Research ->
    Reports), rendered with plain nested `st.expander`s -- no custom JS."""

    label: str
    kind: str
    children: tuple["DatasetDependencyNode", ...] = ()


@dataclass
class CatalogOverlay:
    """Catalog-only *persisted* fields for one dataset, keyed by dataset
    id. Never a second copy of anything `DatasetManager` already owns
    (name, tags, quality, favorite, archived, ...) -- those are always
    read live from `DatasetManager.get(id)` and merged on top of this at
    read time into a `CatalogRecord` (see `catalog.py`)."""

    dataset_id: str
    owner: str = ""
    catalog_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dataset_id": self.dataset_id, "owner": self.owner, "catalog_notes": self.catalog_notes}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CatalogOverlay":
        return CatalogOverlay(dataset_id=data["dataset_id"], owner=data.get("owner", ""), catalog_notes=data.get("catalog_notes", ""))


@dataclass(frozen=True)
class CatalogRecord:
    """The full, read-only, merged catalog view of one dataset -- every
    field the Phase 17.5 spec requires "every dataset must expose",
    combining live `DatasetRecord` truth with the `CatalogOverlay` (owner/
    catalog notes). Built by `DataCatalog.list_catalog()`/`get()`; never
    persisted itself (the overlay is what's persisted)."""

    id: str
    filename: str
    display_name: str
    description: str
    owner: str
    created: datetime
    modified: datetime
    imported: datetime
    last_used: datetime | None
    source: str
    hash: str
    version_count: int
    tags: tuple[str, ...]
    quality_score: int
    favorite: bool
    archived: bool
    protected: bool


class CatalogAuditEventType(str, Enum):
    IMPORTED = "IMPORTED"
    VALIDATED = "VALIDATED"
    REINDEXED = "REINDEXED"
    RENAMED = "RENAMED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    DELETED = "DELETED"
    REFERENCED = "REFERENCED"


@dataclass(frozen=True)
class CatalogAuditEvent:
    """One offline, timestamp-only catalog audit entry -- mirrors
    `app.dataset_manager.models.DatasetAuditEvent` exactly."""

    event_type: CatalogAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CatalogAuditEvent":
        return CatalogAuditEvent(
            event_type=CatalogAuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class DataCatalogState:
    """The full persisted catalog state: per-dataset overlay records, the
    usage-context log (capped), and the last-synced lineage events
    (capped per dataset) -- one JSON document, mirrors
    `DatasetManagerState`'s shape."""

    records: dict[str, CatalogOverlay] = field(default_factory=dict)
    usage_contexts: list[DatasetUsageContext] = field(default_factory=list)
    lineage_events: dict[str, list[DatasetLineageEvent]] = field(default_factory=dict)
    last_synced_job_created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": {key: rec.to_dict() for key, rec in self.records.items()},
            "usage_contexts": [u.to_dict() for u in self.usage_contexts],
            "lineage_events": {key: [e.to_dict() for e in events] for key, events in self.lineage_events.items()},
            "last_synced_job_created_at": self.last_synced_job_created_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DataCatalogState":
        return DataCatalogState(
            records={key: CatalogOverlay.from_dict(rec) for key, rec in data.get("records", {}).items()},
            usage_contexts=[DatasetUsageContext.from_dict(u) for u in data.get("usage_contexts", [])],
            lineage_events={
                key: [DatasetLineageEvent.from_dict(e) for e in events] for key, events in data.get("lineage_events", {}).items()
            },
            last_synced_job_created_at=data.get("last_synced_job_created_at"),
        )
