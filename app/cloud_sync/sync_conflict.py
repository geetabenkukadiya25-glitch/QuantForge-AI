"""Conflict model (Phase 17.9). Since no real remote exists, "remote"
hash/timestamp values are always caller-supplied (e.g. from a manually
entered comparison, or a future real provider once one exists) --
`classify_conflict` never fabricates a remote value, and nothing here
ever resolves a conflict automatically. Every resolution is an explicit
caller call to `resolve_conflict`.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ConflictKind(str, Enum):
    REMOTE_NEWER = "REMOTE_NEWER"
    LOCAL_NEWER = "LOCAL_NEWER"
    HASH_MISMATCH = "HASH_MISMATCH"
    RENAME_CONFLICT = "RENAME_CONFLICT"
    DELETE_CONFLICT = "DELETE_CONFLICT"
    DUPLICATE_CONFLICT = "DUPLICATE_CONFLICT"


class ConflictResolutionPolicy(str, Enum):
    KEEP_LOCAL = "KEEP_LOCAL"
    KEEP_REMOTE = "KEEP_REMOTE"
    MERGE_LATER = "MERGE_LATER"
    MANUAL = "MANUAL"


@dataclass
class SyncConflict:
    operation_id: str
    artifact_id: str
    kind: ConflictKind
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    local_hash: str | None = None
    remote_hash: str | None = None
    detected_at: datetime = field(default_factory=lambda: datetime.now())
    resolution: ConflictResolutionPolicy | None = None
    resolved_at: datetime | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation_id": self.operation_id,
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "local_hash": self.local_hash,
            "remote_hash": self.remote_hash,
            "detected_at": self.detected_at.isoformat(),
            "resolution": self.resolution.value if self.resolution else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "SyncConflict":
        return SyncConflict(
            id=data["id"],
            operation_id=data["operation_id"],
            artifact_id=data["artifact_id"],
            kind=ConflictKind(data["kind"]),
            local_hash=data.get("local_hash"),
            remote_hash=data.get("remote_hash"),
            detected_at=datetime.fromisoformat(data["detected_at"]),
            resolution=ConflictResolutionPolicy(data["resolution"]) if data.get("resolution") else None,
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            notes=data.get("notes", ""),
        )


def classify_conflict(local_hash: str | None, remote_hash: str | None, local_modified: datetime | None, remote_modified: datetime | None) -> ConflictKind | None:
    """Pure classification over caller-supplied values -- `remote_hash`/
    `remote_modified` never come from a real remote (none exists); a
    caller (test, or a future real provider) supplies them explicitly.
    Returns `None` when there is nothing to reconcile."""
    if local_hash is None or remote_hash is None:
        return None
    if local_hash == remote_hash:
        return None
    if local_modified is not None and remote_modified is not None:
        if remote_modified > local_modified:
            return ConflictKind.REMOTE_NEWER
        if local_modified > remote_modified:
            return ConflictKind.LOCAL_NEWER
    return ConflictKind.HASH_MISMATCH


def resolve_conflict(conflict: SyncConflict, resolution: ConflictResolutionPolicy, notes: str = "") -> SyncConflict:
    """Never automatic -- always an explicit caller decision."""
    conflict.resolution = resolution
    conflict.resolved_at = datetime.now()
    conflict.notes = notes
    return conflict
