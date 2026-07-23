"""Snapshot metadata (Phase 17.9) -- metadata only, no archive/compression
(per spec). A `Snapshot` records WHAT a point-in-time view would consist
of (a list of object references) and a content hash over that reference
list, computed via the project's shared checksum recipe -- it never
copies or compresses the referenced objects' actual data.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.checksums import compute_checksum


class SnapshotKind(str, Enum):
    WORKSPACE = "WORKSPACE"
    DATASET = "DATASET"
    STRATEGY = "STRATEGY"
    PROJECT = "PROJECT"
    SETTINGS = "SETTINGS"


@dataclass
class Snapshot:
    kind: SnapshotKind
    label: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    object_refs: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    content_hash: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "label": self.label,
            "object_refs": list(self.object_refs),
            "created_at": self.created_at.isoformat(),
            "content_hash": self.content_hash,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "Snapshot":
        return Snapshot(
            id=data["id"],
            kind=SnapshotKind(data["kind"]),
            label=data["label"],
            object_refs=list(data.get("object_refs", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
            content_hash=data.get("content_hash", ""),
            notes=data.get("notes", ""),
        )


def create_snapshot(kind: SnapshotKind, label: str, object_refs: list[str], notes: str = "") -> Snapshot:
    refs = list(object_refs)
    return Snapshot(kind=kind, label=label, object_refs=refs, content_hash=compute_checksum(sorted(refs)), notes=notes)
