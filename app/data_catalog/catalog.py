"""Data Catalog orchestrator (Phase 17.5).

`DataCatalog` turns `DatasetManager`'s registry into a governed catalog:
lineage, a dependency tree, usage analytics, catalog-wide search/filters,
and its own audit trail -- a pure metadata/observability layer. It reads
`DatasetManager`/`JobManager`/`StrategyLibraryManager` and never modifies
any of them; its own persisted state is only the owner/notes overlay, the
usage-context observation log, and the last-synced lineage cache.

`sync()` is idempotent and safe to call on every page load (same spirit
as `DatasetManager`'s own read methods) -- it recomputes lineage from
current `DatasetManager`/`JobManager` state each time rather than trying
to incrementally diff, since both source logs are already capped and
small (<=2000 entries).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config.paths import get_paths
from app.data_catalog.audit_log import CatalogAuditLogStore
from app.data_catalog.dependency_graph import build_dependency_tree
from app.data_catalog.models import (
    CatalogAuditEvent,
    CatalogAuditEventType,
    CatalogOverlay,
    CatalogRecord,
    DataCatalogState,
    DatasetDependencyNode,
    DatasetLineageEvent,
    DatasetUsageContext,
    DatasetUsageStats,
    LineageEventKind,
)
from app.data_catalog.usage_tracker import build_exact_lineage_from_audit, build_exact_lineage_from_versions, correlate_job_lineage
from app.dataset_manager import DatasetManager, DatasetRecord
from app.job_manager import get_job_manager
from app.job_manager.job_state import JobState
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_USAGE_CONTEXTS = 2000
_MAX_LINEAGE_EVENTS_PER_DATASET = 200
_USED_BY_KINDS = {
    LineageEventKind.USED_BY_BACKTEST,
    LineageEventKind.USED_BY_OPTIMIZATION,
    LineageEventKind.USED_BY_VALIDATION,
    LineageEventKind.USED_BY_REPLAY,
    LineageEventKind.USED_BY_RESEARCH,
    LineageEventKind.USED_BY_PORTFOLIO,
    LineageEventKind.USED_BY_REPORTS,
    LineageEventKind.USED_BY_OTHER,
}


class DataCatalog:
    def __init__(self, state_dir: Path | None = None, dataset_manager: DatasetManager | None = None, job_manager=None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.data_catalog_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._datasets = dataset_manager or DatasetManager()
        self._jobs = job_manager or get_job_manager()
        self._audit_log = CatalogAuditLogStore(self._state_dir)

    # ------------------------------------------------------------------
    # Catalog listing / search / filter
    # ------------------------------------------------------------------

    def _to_catalog_record(self, record: DatasetRecord, overlay: CatalogOverlay | None) -> CatalogRecord:
        health = self._datasets.get_health(record.id)
        return CatalogRecord(
            id=record.id,
            filename=record.filename,
            display_name=record.display_name,
            description=record.description,
            owner=overlay.owner if overlay else "",
            created=record.created,
            modified=record.modified,
            imported=record.import_date,
            last_used=record.last_used,
            source=record.source.value,
            hash=record.hash,
            version_count=len(self._datasets.list_versions(record.id)),
            tags=tuple(record.tags),
            quality_score=health.score,
            favorite=record.favorite,
            archived=record.archived,
            protected=record.protected,
        )

    def list_catalog(self, archived: bool | None = False) -> list[CatalogRecord]:
        state = self._load_state()
        return [self._to_catalog_record(r, state.records.get(r.id)) for r in self._datasets.list_entries(archived=archived)]

    def get(self, dataset_id: str) -> CatalogRecord:
        state = self._load_state()
        record = self._datasets.get(dataset_id)
        return self._to_catalog_record(record, state.records.get(dataset_id))

    def search(self, query: str) -> list[CatalogRecord]:
        from app.data_catalog.search import search_catalog

        return search_catalog(self.list_catalog(archived=None), query)

    def filter_entries(
        self,
        favorite: bool | None = None,
        archived: bool | None = None,
        protected: bool | None = None,
        recently_used: bool | None = None,
        min_quality: int | None = None,
    ) -> list[CatalogRecord]:
        from app.data_catalog.search import filter_catalog

        return filter_catalog(
            self.list_catalog(archived=None),
            favorite=favorite,
            archived=archived,
            protected=protected,
            recently_used=recently_used,
            min_quality=min_quality,
        )

    def catalog_statistics(self) -> dict:
        entries = self.list_catalog(archived=None)
        active = [e for e in entries if not e.archived]
        return {
            "total_datasets": len(entries),
            "active_datasets": len(active),
            "archived_datasets": len(entries) - len(active),
            "favorites": sum(1 for e in entries if e.favorite),
            "protected": sum(1 for e in entries if e.protected),
            "average_quality": round(sum(e.quality_score for e in active) / len(active), 1) if active else None,
        }

    # ------------------------------------------------------------------
    # Owner / catalog notes overlay
    # ------------------------------------------------------------------

    def set_owner(self, dataset_id: str, owner: str) -> CatalogRecord:
        state = self._load_state()
        overlay = state.records.setdefault(dataset_id, CatalogOverlay(dataset_id=dataset_id))
        overlay.owner = owner
        self._save_state(state)
        return self.get(dataset_id)

    def set_catalog_notes(self, dataset_id: str, notes: str) -> CatalogRecord:
        state = self._load_state()
        overlay = state.records.setdefault(dataset_id, CatalogOverlay(dataset_id=dataset_id))
        overlay.catalog_notes = notes
        self._save_state(state)
        return self.get(dataset_id)

    # ------------------------------------------------------------------
    # Usage context (written by the dataset_picker hook)
    # ------------------------------------------------------------------

    def record_usage_context(self, page_key: str, dataset_id: str) -> None:
        state = self._load_state()
        state.usage_contexts.append(DatasetUsageContext(page_key=page_key, dataset_id=dataset_id, timestamp=datetime.now(timezone.utc)))
        del state.usage_contexts[:-_MAX_USAGE_CONTEXTS]
        self._save_state(state)

    # ------------------------------------------------------------------
    # Lineage sync
    # ------------------------------------------------------------------

    def sync(self) -> int:
        """Recompute lineage for every dataset from current
        `DatasetManager` audit/version data plus job-history correlation.
        Returns the number of lineage events written. Never touches
        `DatasetManager`'s or `JobManager`'s own state."""
        state = self._load_state()
        job_records = list(self._jobs.history(limit=2000))
        live_ids = {r.id for r in job_records}
        for job in self._jobs.list():
            if job.id not in live_ids:
                job_records.append(job.to_record())

        correlated = correlate_job_lineage(job_records, state.usage_contexts)
        new_referenced_ids = {e.dataset_id for e in correlated}

        by_dataset: dict[str, list[DatasetLineageEvent]] = {}
        for event in correlated:
            by_dataset.setdefault(event.dataset_id, []).append(event)

        total = 0
        for record in self._datasets.list_entries(archived=None):
            exact = build_exact_lineage_from_audit(
                record.id, self._datasets.list_audit_events(record.id, limit=200)
            ) + build_exact_lineage_from_versions(record.id, self._datasets.list_versions(record.id))
            combined = exact + by_dataset.get(record.id, [])
            combined.sort(key=lambda e: e.timestamp, reverse=True)
            state.lineage_events[record.id] = combined[:_MAX_LINEAGE_EVENTS_PER_DATASET]
            total += len(combined)

        self._save_state(state)
        for dataset_id in new_referenced_ids:
            self._audit_log.record(CatalogAuditEventType.REFERENCED, dataset_id)
        return total

    def lineage(self, dataset_id: str) -> list[DatasetLineageEvent]:
        state = self._load_state()
        return list(state.lineage_events.get(dataset_id, []))

    def dependency_tree(self, dataset_id: str) -> DatasetDependencyNode:
        from app.strategy_library import StrategyLibraryManager

        record = self._datasets.get(dataset_id)
        try:
            strategy_names = [e.name for e in StrategyLibraryManager().list_entries()]
        except Exception:  # noqa: BLE001 -- dependency tree must never crash over strategy library lookup
            strategy_names = []
        return build_dependency_tree(record.display_name, self.lineage(dataset_id), strategy_names)

    def usage_stats(self, dataset_id: str) -> DatasetUsageStats:
        record = self._datasets.get(dataset_id)
        events = [e for e in self.lineage(dataset_id) if e.kind in _USED_BY_KINDS]

        live_by_id = {j.id: j for j in self._jobs.list()}
        elapsed: list[float] = []
        completed = 0
        current = 0
        for event in events:
            job = live_by_id.get(event.job_id) if event.job_id else None
            if job is not None:
                if job.state in (JobState.RUNNING, JobState.QUEUED):
                    current += 1
                if job.elapsed_seconds is not None:
                    elapsed.append(job.elapsed_seconds)
            if event.status == JobState.COMPLETED.value:
                completed += 1

        strategies_referencing = len(
            {n.label for n in self.dependency_tree(dataset_id).children if n.kind == "Strategy" and n.label != "(unattributed)"}
        )

        return DatasetUsageStats(
            times_used=len(events),
            last_used=record.last_used,
            current_jobs=current,
            completed_jobs=completed,
            strategies_referencing=strategies_referencing,
            reports_generated=sum(1 for e in events if e.kind == LineageEventKind.USED_BY_REPORTS),
            validation_runs=sum(1 for e in events if e.kind == LineageEventKind.USED_BY_VALIDATION),
            optimization_runs=sum(1 for e in events if e.kind == LineageEventKind.USED_BY_OPTIMIZATION),
            replay_runs=sum(1 for e in events if e.kind == LineageEventKind.USED_BY_REPLAY),
            average_runtime_seconds=(sum(elapsed) / len(elapsed)) if elapsed else None,
        )

    def impact(self, dataset_id: str) -> dict:
        """Read-only "referenced by" summary for the delete/archive
        warning -- never blocks the underlying `DatasetManager` action."""
        events = [e for e in self.lineage(dataset_id) if e.kind in _USED_BY_KINDS]
        tree = self.dependency_tree(dataset_id)
        return {
            "strategies": sum(1 for n in tree.children if n.kind == "Strategy" and n.label != "(unattributed)"),
            "backtests": sum(1 for e in events if e.kind == LineageEventKind.USED_BY_BACKTEST),
            "optimizations": sum(1 for e in events if e.kind == LineageEventKind.USED_BY_OPTIMIZATION),
            "validations": sum(1 for e in events if e.kind == LineageEventKind.USED_BY_VALIDATION),
            "replay_sessions": sum(1 for e in events if e.kind == LineageEventKind.USED_BY_REPLAY),
            "reports": sum(1 for e in events if e.kind == LineageEventKind.USED_BY_REPORTS),
            "total_references": len(events),
        }

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def audit_events(self, dataset_id: str | None = None, limit: int = 200) -> list[CatalogAuditEvent]:
        return self._audit_log.list_events(key=dataset_id, limit=limit)

    # ------------------------------------------------------------------
    # Internal state persistence
    # ------------------------------------------------------------------

    def _state_file(self) -> Path:
        return self._state_dir / "catalog_state.json"

    def _load_state(self) -> DataCatalogState:
        file = self._state_file()
        if not file.exists():
            return DataCatalogState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Data catalog state file is unreadable; starting fresh.")
            return DataCatalogState()
        return DataCatalogState.from_dict(data)

    def _save_state(self, state: DataCatalogState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
