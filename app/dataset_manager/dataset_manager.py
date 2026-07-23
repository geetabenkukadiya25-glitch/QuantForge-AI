"""Dataset Manager orchestrator (Phase 18.6).

`DatasetManager` turns the previously session-only, ad-hoc dataset upload
flow into a full offline dataset management system: import (with
content-hash dedup), search/filter, favorites/tags/archive, versioning,
audit log, validation/health, and export -- every imported dataset
becomes a persistent, managed asset under `Paths.dataset_registry_dir` /
`Paths.dataset_manager_state_dir`.

Pure orchestration + file-management layer -- it NEVER reimplements CSV
parsing, cleaning, validation, or export (always delegates to
`app.data_engine`) and NEVER touches any trading/strategy/backtesting
engine. `app/ui/state.py`'s session-slot API is untouched; this manager
is the persistent registry underneath it -- pages that want the "active
this session" dataset still call `app.ui.state.save_dataset(...)` with
whatever `DatasetManager.load_dataframe(...)` returns.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.config.paths import get_paths
from app.data_engine.validator import ValidationResult
from app.dataset_manager.audit_log import DatasetAuditLogStore
from app.dataset_manager.exceptions import DatasetNotFoundError, ProtectedDatasetError
from app.dataset_manager.exporter import DatasetExporter, ExportFormat
from app.dataset_manager.importer import DatasetImporter, hash_bytes
from app.dataset_manager.models import (
    DatasetAuditEventType,
    DatasetHealth,
    DatasetManagerState,
    DatasetPreview,
    DatasetRecord,
    DatasetSource,
    DatasetStatistics,
    DatasetVersion,
    DatasetVersionEventType,
)
from app.dataset_manager.search import filter_records, search_records
from app.dataset_manager.statistics import compute_statistics
from app.dataset_manager.validator import DatasetValidator
from app.ui.dataset_detection import detect_symbol_from_filename, detect_timeframe_from_datetime, detect_timeframe_from_filename
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_VERSIONS_PER_DATASET = 20
_PREVIEW_ROWS = 100


class DatasetManager:
    """CRUD + search/filter/favorites/tags/archive/versioning/audit over
    managed datasets, backed by one CSV copy per dataset plus a single
    JSON state document (mirrors `StrategyLibraryManager`'s shape)."""

    def __init__(
        self,
        registry_dir: Path | None = None,
        state_dir: Path | None = None,
        importer: DatasetImporter | None = None,
        exporter: DatasetExporter | None = None,
        validator: DatasetValidator | None = None,
    ) -> None:
        paths = get_paths()
        self._registry_dir = registry_dir or paths.dataset_registry_dir
        self._state_dir = state_dir or paths.dataset_manager_state_dir
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._importer = importer or DatasetImporter(self._registry_dir)
        self._exporter = exporter or DatasetExporter()
        self._validator = validator or DatasetValidator()
        self._audit_log = DatasetAuditLogStore(self._state_dir)
        self._health_cache: dict[str, DatasetHealth] = {}

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_dataset_from_bytes(
        self,
        data: bytes,
        filename: str,
        display_name: str | None = None,
        tags: tuple[str, ...] = (),
        description: str = "",
        notes: str = "",
        source: DatasetSource = DatasetSource.UPLOAD,
        clean: bool = True,
    ) -> DatasetRecord:
        """Import `data`. If content with the same SHA-256 hash is already
        registered, returns the EXISTING record instead of creating a
        duplicate -- "prevent duplicate imports" (Dataset Cache)."""
        content_hash = hash_bytes(data)
        existing = self._find_by_hash(content_hash)
        if existing is not None:
            logger.info("Duplicate import detected for hash %s; reusing dataset %s.", content_hash[:12], existing.id)
            return existing

        record, df = self._importer.import_from_bytes(
            data, filename, display_name=display_name, tags=tags, description=description, notes=notes, source=source, clean=clean
        )
        self._compute_and_stash_health(record, df)
        return self._finish_import(record)

    def import_dataset_from_path(
        self,
        path: str | Path,
        display_name: str | None = None,
        tags: tuple[str, ...] = (),
        description: str = "",
        notes: str = "",
    ) -> DatasetRecord:
        path = Path(path)
        data = path.read_bytes()
        return self.import_dataset_from_bytes(
            data, filename=path.name, display_name=display_name, tags=tags, description=description, notes=notes, source=DatasetSource.IMPORT
        )

    def _finish_import(self, record: DatasetRecord) -> DatasetRecord:
        state = self._load_state()
        state.records[record.id] = record
        self._append_version(state, record.id, DatasetVersionEventType.IMPORTED)
        self._save_state(state)
        self._audit_log.record(DatasetAuditEventType.IMPORTED, record.id)
        return record

    def _compute_and_stash_health(self, record: DatasetRecord, df: pd.DataFrame) -> DatasetHealth:
        _, health = self._validator.validate(df, timeframe=record.timeframe)
        self._health_cache[record.id] = health
        return health

    # ------------------------------------------------------------------
    # Listing / browsing
    # ------------------------------------------------------------------

    def list_entries(self, archived: bool | None = False) -> list[DatasetRecord]:
        """Every registered dataset, favorites first. `archived=False`
        (default) excludes archived datasets; pass `None` for everything."""
        state = self._load_state()
        records = list(state.records.values())
        if archived is not None:
            records = [r for r in records if r.archived == archived]
        records.sort(key=lambda r: (not r.favorite, r.display_name.lower()))
        return records

    def get(self, dataset_id: str) -> DatasetRecord:
        state = self._load_state()
        record = state.records.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(f"No dataset with id '{dataset_id}'.")
        return record

    def search(self, query: str) -> list[DatasetRecord]:
        return search_records(self.list_entries(archived=None), query)

    def filter_entries(
        self, favorite: bool | None = None, archived: bool | None = None, tags: list[str] | None = None, source: str | None = None
    ) -> list[DatasetRecord]:
        return filter_records(self.list_entries(archived=None), favorite=favorite, archived=archived, tags=tags, source=source)

    def list_recent(self, limit: int = 10) -> list[DatasetRecord]:
        records = [r for r in self.list_entries(archived=None) if r.last_used is not None]
        records.sort(key=lambda r: r.last_used, reverse=True)
        return records[:limit]

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        record = self.get(dataset_id)
        return self._importer.load_dataframe(record)

    def preview(self, dataset_id: str, n: int = _PREVIEW_ROWS) -> DatasetPreview:
        from app.dataset_manager.models import ColumnInfo

        df = self.load_dataframe(dataset_id)
        head = df.head(n)
        columns = tuple(
            ColumnInfo(name=col, dtype=str(df[col].dtype), null_count=int(df[col].isna().sum()), unique_count=int(df[col].nunique()))
            for col in df.columns
        )
        rows = tuple(head.astype(object).where(head.notna(), None).to_dict(orient="records"))
        return DatasetPreview(columns=columns, rows=rows, total_rows=len(df))

    def record_used(self, dataset_id: str) -> DatasetRecord:
        """Bump `last_used` -- called whenever a dashboard loads this
        dataset into the shared session slot."""
        state = self._load_state()
        record = state.records.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(f"No dataset with id '{dataset_id}'.")
        record.last_used = datetime.now(timezone.utc)
        self._save_state(state)
        return record

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def rename(self, dataset_id: str, new_display_name: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.display_name = new_display_name
        record.modified = datetime.now(timezone.utc)
        self._save_state(state)
        self._audit_log.record(DatasetAuditEventType.RENAMED, dataset_id)
        return record

    def duplicate(self, dataset_id: str) -> DatasetRecord:
        record = self.get(dataset_id)
        data = (self._registry_dir / f"{record.id}.csv").read_bytes()
        new_record, df = self._importer.import_from_bytes(
            data,
            filename=record.filename,
            display_name=f"{record.display_name} (copy)",
            tags=tuple(record.tags),
            description=record.description,
            notes=record.notes,
            source=DatasetSource.DUPLICATE,
        )
        # Duplicates are deliberately allowed to share content with their
        # source (that's the point) -- give it a fresh hash-independent id
        # path so cache lookups on the ORIGINAL's hash keep resolving to
        # the original, not silently redirecting future imports here.
        new_record.hash = f"{new_record.hash}:{new_record.id}"
        self._compute_and_stash_health(new_record, df)
        return self._finish_import(new_record)

    def archive(self, dataset_id: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.archived = True
        record.modified = datetime.now(timezone.utc)
        self._append_version(state, dataset_id, DatasetVersionEventType.ARCHIVED)
        self._save_state(state)
        self._audit_log.record(DatasetAuditEventType.ARCHIVED, dataset_id)
        return record

    def restore(self, dataset_id: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.archived = False
        record.modified = datetime.now(timezone.utc)
        self._save_state(state)
        self._audit_log.record(DatasetAuditEventType.RESTORED, dataset_id)
        return record

    def delete(self, dataset_id: str) -> None:
        state = self._load_state()
        record = self._require(state, dataset_id)
        if record.protected:
            raise ProtectedDatasetError(f"Dataset '{record.display_name}' is protected; unprotect it before deleting.")
        del state.records[dataset_id]
        state.versions.pop(dataset_id, None)
        self._save_state(state)
        (self._registry_dir / f"{dataset_id}.csv").unlink(missing_ok=True)
        self._audit_log.record(DatasetAuditEventType.DELETED, dataset_id)

    def toggle_favorite(self, dataset_id: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.favorite = not record.favorite
        self._save_state(state)
        return record

    def set_protected(self, dataset_id: str, protected: bool) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.protected = protected
        self._save_state(state)
        return record

    def add_tags(self, dataset_id: str, tags: list[str]) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.tags = sorted(set(record.tags) | set(tags))
        self._save_state(state)
        return record

    def remove_tags(self, dataset_id: str, tags: list[str]) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.tags = [t for t in record.tags if t not in set(tags)]
        self._save_state(state)
        return record

    def set_description(self, dataset_id: str, description: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.description = description
        self._save_state(state)
        return record

    def set_notes(self, dataset_id: str, notes: str) -> DatasetRecord:
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.notes = notes
        self._save_state(state)
        return record

    # ------------------------------------------------------------------
    # Validation / statistics / metadata refresh
    # ------------------------------------------------------------------

    def revalidate(self, dataset_id: str) -> tuple[ValidationResult, DatasetHealth]:
        record = self.get(dataset_id)
        df = self.load_dataframe(dataset_id)
        result, health = self._validator.validate(df, timeframe=record.timeframe)
        state = self._load_state()
        stored = self._require(state, dataset_id)
        stored.missing_values = sum(result.missing_values.values())
        stored.duplicate_rows = result.duplicate_candles
        stored.modified = datetime.now(timezone.utc)
        self._append_version(state, dataset_id, DatasetVersionEventType.REVALIDATED)
        self._save_state(state)
        self._audit_log.record(DatasetAuditEventType.REVALIDATED, dataset_id)
        self._health_cache[dataset_id] = health
        return result, health

    def reindex(self, dataset_id: str) -> DatasetStatistics:
        """Recompute statistics from the stored file (e.g. after an
        out-of-band edit to the registry copy)."""
        from app.data_engine.loader import DataLoader

        record = self.get(dataset_id)
        df = self.load_dataframe(dataset_id)
        loader_stats = DataLoader().statistics(df)
        disk_size = (self._registry_dir / f"{dataset_id}.csv").stat().st_size
        stats = compute_statistics(df, loader_stats, disk_size, record.symbol, record.timeframe)

        state = self._load_state()
        stored = self._require(state, dataset_id)
        stored.rows = stats.rows
        stored.columns = stats.columns
        stored.candles = stats.candles
        stored.file_size = disk_size
        stored.modified = datetime.now(timezone.utc)
        self._append_version(state, dataset_id, DatasetVersionEventType.REINDEXED)
        self._save_state(state)
        return stats

    def refresh_metadata(self, dataset_id: str) -> DatasetRecord:
        df = self.load_dataframe(dataset_id)
        state = self._load_state()
        record = self._require(state, dataset_id)
        record.symbol = detect_symbol_from_filename(record.filename) or record.symbol
        record.timeframe = detect_timeframe_from_filename(record.filename) or detect_timeframe_from_datetime(df) or record.timeframe
        record.modified = datetime.now(timezone.utc)
        self._append_version(state, dataset_id, DatasetVersionEventType.UPDATED)
        self._save_state(state)
        return record

    def generate_statistics(self, dataset_id: str) -> DatasetStatistics:
        return self.reindex(dataset_id)

    def get_health(self, dataset_id: str) -> DatasetHealth:
        if dataset_id in self._health_cache:
            return self._health_cache[dataset_id]
        _, health = self.revalidate(dataset_id)
        return health

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, dataset_id: str, target_path: str | Path, fmt: ExportFormat) -> Path:
        df = self.load_dataframe(dataset_id)
        path = self._exporter.export(df, target_path, fmt)
        self._audit_log.record(DatasetAuditEventType.EXPORTED, dataset_id)
        return path

    # ------------------------------------------------------------------
    # Version history / audit log
    # ------------------------------------------------------------------

    def list_versions(self, dataset_id: str) -> list[DatasetVersion]:
        state = self._load_state()
        return list(state.versions.get(dataset_id, []))

    def list_audit_events(self, dataset_id: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=dataset_id, limit=limit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_by_hash(self, content_hash: str) -> DatasetRecord | None:
        state = self._load_state()
        for record in state.records.values():
            if record.hash == content_hash:
                return record
        return None

    def _require(self, state: DatasetManagerState, dataset_id: str) -> DatasetRecord:
        record = state.records.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(f"No dataset with id '{dataset_id}'.")
        return record

    def _append_version(self, state: DatasetManagerState, dataset_id: str, event_type: DatasetVersionEventType, note: str = "") -> None:
        versions = state.versions.setdefault(dataset_id, [])
        versions.append(DatasetVersion(event_type=event_type, timestamp=datetime.now(timezone.utc), note=note))
        del versions[:-_MAX_VERSIONS_PER_DATASET]

    def _state_file(self) -> Path:
        return self._state_dir / "dataset_state.json"

    def _load_state(self) -> DatasetManagerState:
        file = self._state_file()
        if not file.exists():
            return DatasetManagerState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Dataset manager state file is unreadable; starting fresh.")
            return DatasetManagerState()
        return DatasetManagerState.from_dict(data)

    def _save_state(self, state: DatasetManagerState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
