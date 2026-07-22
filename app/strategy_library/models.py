"""Data models for Strategy Library management (Phase 18).

These are presentation/management-layer records ONLY -- they describe a
strategy *file* (where it lives, whether it's protected, its favorite/
validation/recency status) and never redefine or duplicate `app.sdl`'s
`StrategyDefinition` schema. A `LibraryEntry` is built by summarizing an
already-parsed/validated `StrategyDefinition`, exactly like
`app.sdl.registry.StrategySummary` does for the plain registry.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class StrategySource(str, Enum):
    """Where a strategy file lives -- determines protection rules."""

    EXAMPLE = "EXAMPLE"
    USER = "USER"


class ValidationBadge(str, Enum):
    """At-a-glance validation status shown without opening the strategy."""

    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"


@dataclass(frozen=True)
class LibraryEntry:
    """One row in the Strategy Library browser: everything needed to
    render a list/search/filter/favorite/badge UI without re-parsing the
    file on every interaction."""

    path: Path
    filename: str
    source: StrategySource
    strategy_id: str
    name: str
    strategy_version: str
    sdl_version: str
    author: str | None
    category: str | None
    tags: tuple[str, ...]
    asset_class: str | None
    market_type: str | None
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    primary_timeframe: str | None
    sessions: tuple[str, ...]
    indicator_names: tuple[str, ...]
    execution_type: str | None
    risk_model_summary: str | None
    created_at: datetime | None
    modified_at: datetime | None
    validation_badge: ValidationBadge
    validation_summary: str
    is_favorite: bool = False
    description: str | None = None
    entry_rule_conditions: tuple[str, ...] = ()
    exit_rule_conditions: tuple[str, ...] = ()

    @property
    def is_protected(self) -> bool:
        return self.source == StrategySource.EXAMPLE


@dataclass(frozen=True)
class VersionSnapshot:
    """One immutable, restorable revision of a strategy file's content,
    recorded on every `StrategyLibraryManager.save()`."""

    version_id: int
    saved_at: datetime
    fmt: str
    content: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "saved_at": self.saved_at.isoformat(),
            "fmt": self.fmt,
            "content": self.content,
            "note": self.note,
        }

    @staticmethod
    def from_dict(data: dict) -> "VersionSnapshot":
        return VersionSnapshot(
            version_id=data["version_id"],
            saved_at=datetime.fromisoformat(data["saved_at"]),
            fmt=data["fmt"],
            content=data["content"],
            note=data.get("note", ""),
        )


@dataclass(frozen=True)
class CompileRecord:
    """The outcome of the most recent `StrategyCompiler.compile()` attempt
    for one strategy file -- recorded by the management layer, never by
    the compiler itself (Phase 18 rule 22: "Compile Status")."""

    compiled_at: datetime
    success: bool
    duration_seconds: float
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "compiled_at": self.compiled_at.isoformat(),
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }

    @staticmethod
    def from_dict(data: dict) -> "CompileRecord":
        return CompileRecord(
            compiled_at=datetime.fromisoformat(data["compiled_at"]),
            success=data["success"],
            duration_seconds=data["duration_seconds"],
            error_message=data.get("error_message"),
        )


@dataclass(frozen=True)
class AutosaveRecord:
    """A local, timestamped autosave snapshot -- never overwrites the
    original file; only ever written under `Paths.sdl_autosave_dir`."""

    key: str
    saved_at: datetime
    fmt: str
    content: str
    original_key: str | None
    """The strategy this autosave belongs to (`None` for a not-yet-saved new strategy)."""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "saved_at": self.saved_at.isoformat(),
            "fmt": self.fmt,
            "content": self.content,
            "original_key": self.original_key,
        }

    @staticmethod
    def from_dict(data: dict) -> "AutosaveRecord":
        return AutosaveRecord(
            key=data["key"],
            saved_at=datetime.fromisoformat(data["saved_at"]),
            fmt=data["fmt"],
            content=data["content"],
            original_key=data.get("original_key"),
        )


@dataclass(frozen=True)
class LockInfo:
    """A soft, single-machine editing lock -- prevents two editor sessions
    in the same running app from silently clobbering each other's saves.
    Not a distributed/multi-machine lock (offline, single-process tool)."""

    owner_token: str
    acquired_at: datetime
    heartbeat_at: datetime

    def to_dict(self) -> dict:
        return {
            "owner_token": self.owner_token,
            "acquired_at": self.acquired_at.isoformat(),
            "heartbeat_at": self.heartbeat_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "LockInfo":
        return LockInfo(
            owner_token=data["owner_token"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            heartbeat_at=datetime.fromisoformat(data["heartbeat_at"]),
        )


class AuditEventType(str, Enum):
    CREATED = "CREATED"
    OPENED = "OPENED"
    EDITED = "EDITED"
    SAVED = "SAVED"
    COMPILED = "COMPILED"
    VALIDATED = "VALIDATED"
    EXPORTED = "EXPORTED"
    IMPORTED = "IMPORTED"
    DELETED = "DELETED"


@dataclass(frozen=True)
class AuditEvent:
    """One offline, timestamp-only audit trail entry (Phase 18 rule 29).
    No user identity, no network call -- a local record of what happened
    to which strategy file, when."""

    event_type: AuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "AuditEvent":
        return AuditEvent(
            event_type=AuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass(frozen=True)
class StrategyStatistics:
    """Phase 18 rule 24: at-a-glance structural stats about one document."""

    lines_of_sdl: int
    indicator_count: int
    condition_count: int
    filter_count: int
    risk_rule_count: int
    execution_rule_count: int
    metadata_completeness_pct: int


@dataclass(frozen=True)
class Suggestion:
    """A non-blocking, management-layer improvement hint -- distinct from
    `app.sdl.validator.ValidationIssue` (errors/warnings), which is never
    modified or extended by this module."""

    path: str
    message: str


@dataclass
class LibraryState:
    """The full persisted management state: favorites, recently-opened
    strategies, and per-strategy version history. Keyed by a stable,
    portable relative-path string (`StrategyLibraryManager._state_key`),
    never by strategy id (a file can be renamed/duplicated independently
    of its declared SDL id)."""

    favorites: list[str] = field(default_factory=list)
    recent: list[str] = field(default_factory=list)
    versions: dict[str, list[VersionSnapshot]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "favorites": list(self.favorites),
            "recent": list(self.recent),
            "versions": {key: [v.to_dict() for v in snaps] for key, snaps in self.versions.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "LibraryState":
        return LibraryState(
            favorites=list(data.get("favorites", [])),
            recent=list(data.get("recent", [])),
            versions={
                key: [VersionSnapshot.from_dict(v) for v in snaps]
                for key, snaps in data.get("versions", {}).items()
            },
        )
