"""Data classes/enums for Dataset Manager (Phase 18.6). No logic beyond
`to_dict`/`from_dict` -- every persisted record round-trips through these
exactly like `app.strategy_library.models`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Suggested tags a user can pick from in the UI -- datasets may also carry
# any free-form tag string; this is not an enforced enum.
STANDARD_TAGS: tuple[str, ...] = ("Forex", "Crypto", "Stocks", "Gold", "SMC", "ICT", "Scalping", "Swing")


class DatasetSource(str, Enum):
    UPLOAD = "UPLOAD"
    IMPORT = "IMPORT"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class ColumnInfo:
    """One column's descriptive profile, used only by `DatasetPreview`."""

    name: str
    dtype: str
    null_count: int
    unique_count: int


@dataclass(frozen=True)
class DatasetPreview:
    """Runtime-only (never persisted): the first `n` rows of a dataset plus
    a per-column profile, for read-only display in the Dataset Manager."""

    columns: tuple[ColumnInfo, ...]
    rows: tuple[dict[str, Any], ...]
    total_rows: int


@dataclass(frozen=True)
class DatasetStatistics:
    """Phase 18.6: at-a-glance structural stats about one dataset."""

    rows: int
    columns: int
    candles: int
    date_range_start: str | None
    date_range_end: str | None
    symbol: str | None
    timeframe: str | None
    sessions: int
    memory_usage_bytes: int
    disk_size_bytes: int
    frequency: str | None

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "candles": self.candles,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "sessions": self.sessions,
            "memory_usage_bytes": self.memory_usage_bytes,
            "disk_size_bytes": self.disk_size_bytes,
            "frequency": self.frequency,
        }

    @staticmethod
    def from_dict(data: dict) -> "DatasetStatistics":
        return DatasetStatistics(
            rows=data["rows"],
            columns=data["columns"],
            candles=data["candles"],
            date_range_start=data.get("date_range_start"),
            date_range_end=data.get("date_range_end"),
            symbol=data.get("symbol"),
            timeframe=data.get("timeframe"),
            sessions=data.get("sessions", 0),
            memory_usage_bytes=data.get("memory_usage_bytes", 0),
            disk_size_bytes=data.get("disk_size_bytes", 0),
            frequency=data.get("frequency"),
        )


@dataclass(frozen=True)
class HealthCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class DatasetHealth:
    """A 0-100 quality score plus the individual checks behind it (Phase
    18.6's "Dataset Quality"/"Dataset Health Card")."""

    score: int
    checks: tuple[HealthCheck, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    suggestions: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "checks": [{"name": c.name, "passed": c.passed, "message": c.message} for c in self.checks],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "suggestions": list(self.suggestions),
        }

    @staticmethod
    def from_dict(data: dict) -> "DatasetHealth":
        return DatasetHealth(
            score=data["score"],
            checks=tuple(HealthCheck(name=c["name"], passed=c["passed"], message=c["message"]) for c in data.get("checks", [])),
            warnings=tuple(data.get("warnings", [])),
            errors=tuple(data.get("errors", [])),
            suggestions=tuple(data.get("suggestions", [])),
        )


class DatasetVersionEventType(str, Enum):
    CREATED = "CREATED"
    IMPORTED = "IMPORTED"
    UPDATED = "UPDATED"
    REINDEXED = "REINDEXED"
    REVALIDATED = "REVALIDATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class DatasetVersion:
    """One lifecycle checkpoint for a dataset record (Phase 18.6 "Dataset
    Versioning") -- a snapshot of the record's key fields at that point,
    not a second copy of the raw data."""

    event_type: DatasetVersionEventType
    timestamp: datetime
    note: str = ""

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "timestamp": self.timestamp.isoformat(), "note": self.note}

    @staticmethod
    def from_dict(data: dict) -> "DatasetVersion":
        return DatasetVersion(
            event_type=DatasetVersionEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            note=data.get("note", ""),
        )


class DatasetAuditEventType(str, Enum):
    IMPORTED = "IMPORTED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    REVALIDATED = "REVALIDATED"
    EXPORTED = "EXPORTED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"


@dataclass(frozen=True)
class DatasetAuditEvent:
    """One offline, timestamp-only audit trail entry -- mirrors
    `app.strategy_library.models.AuditEvent` exactly."""

    event_type: DatasetAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "DatasetAuditEvent":
        return DatasetAuditEvent(
            event_type=DatasetAuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class DatasetRecord:
    """The managed asset record for one imported dataset. The raw CSV
    itself lives on disk under `Paths.dataset_registry_dir / f"{id}.csv"`;
    this record is everything about it."""

    id: str
    filename: str
    display_name: str
    import_date: datetime
    created: datetime
    modified: datetime
    file_size: int
    rows: int
    columns: int
    candles: int
    symbol: str | None
    timeframe: str | None
    hash: str
    source: DatasetSource

    last_used: datetime | None = None
    timezone: str | None = None
    checksum: str = ""
    encoding: str = "utf-8"
    delimiter: str = ","
    ohlc_mapping: dict[str, str] = field(default_factory=dict)
    volume_mapping: dict[str, str] = field(default_factory=dict)
    spread_mapping: dict[str, str] = field(default_factory=dict)
    missing_values: int = 0
    duplicate_rows: int = 0
    favorite: bool = False
    archived: bool = False
    protected: bool = False
    tags: list[str] = field(default_factory=list)
    description: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "display_name": self.display_name,
            "import_date": self.import_date.isoformat(),
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "file_size": self.file_size,
            "rows": self.rows,
            "columns": self.columns,
            "candles": self.candles,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timezone": self.timezone,
            "source": self.source.value,
            "hash": self.hash,
            "checksum": self.checksum,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "ohlc_mapping": dict(self.ohlc_mapping),
            "volume_mapping": dict(self.volume_mapping),
            "spread_mapping": dict(self.spread_mapping),
            "missing_values": self.missing_values,
            "duplicate_rows": self.duplicate_rows,
            "favorite": self.favorite,
            "archived": self.archived,
            "protected": self.protected,
            "tags": list(self.tags),
            "description": self.description,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "DatasetRecord":
        return DatasetRecord(
            id=data["id"],
            filename=data["filename"],
            display_name=data["display_name"],
            import_date=datetime.fromisoformat(data["import_date"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            file_size=data["file_size"],
            rows=data["rows"],
            columns=data["columns"],
            candles=data["candles"],
            symbol=data.get("symbol"),
            timeframe=data.get("timeframe"),
            timezone=data.get("timezone"),
            source=DatasetSource(data["source"]),
            hash=data["hash"],
            checksum=data.get("checksum", ""),
            encoding=data.get("encoding", "utf-8"),
            delimiter=data.get("delimiter", ","),
            ohlc_mapping=dict(data.get("ohlc_mapping", {})),
            volume_mapping=dict(data.get("volume_mapping", {})),
            spread_mapping=dict(data.get("spread_mapping", {})),
            missing_values=data.get("missing_values", 0),
            duplicate_rows=data.get("duplicate_rows", 0),
            favorite=data.get("favorite", False),
            archived=data.get("archived", False),
            protected=data.get("protected", False),
            tags=list(data.get("tags", [])),
            description=data.get("description", ""),
            notes=data.get("notes", ""),
        )


@dataclass
class DatasetManagerState:
    """The full persisted management state: every dataset record plus
    per-dataset version history. Keyed by `DatasetRecord.id` (a uuid4 hex
    string) -- unlike Strategy Library, datasets have no user-visible file
    path to key off, since the registry owns their on-disk location."""

    records: dict[str, DatasetRecord] = field(default_factory=dict)
    versions: dict[str, list[DatasetVersion]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "records": {key: rec.to_dict() for key, rec in self.records.items()},
            "versions": {key: [v.to_dict() for v in vs] for key, vs in self.versions.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "DatasetManagerState":
        return DatasetManagerState(
            records={key: DatasetRecord.from_dict(rec) for key, rec in data.get("records", {}).items()},
            versions={key: [DatasetVersion.from_dict(v) for v in vs] for key, vs in data.get("versions", {}).items()},
        )
