"""Artifact registry metadata (Phase 17.9). Reuses the project's shared
checksum recipe (`app.core.checksums.compute_checksum`, the same SHA-256
canonical-JSON scheme `BacktestResult.checksum`/`PortfolioResult.checksum`
already use) rather than inventing a second hashing convention.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.checksums import compute_checksum


class ArtifactKind(str, Enum):
    DATASET = "DATASET"
    STRATEGY = "STRATEGY"
    WORKFLOW = "WORKFLOW"
    REPORT = "REPORT"
    RISK_REPORT = "RISK_REPORT"
    GOVERNANCE_REPORT = "GOVERNANCE_REPORT"
    EXPORT = "EXPORT"
    SNAPSHOT = "SNAPSHOT"


class ArtifactStatus(str, Enum):
    REGISTERED = "REGISTERED"
    SYNCED = "SYNCED"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"


@dataclass
class Artifact:
    kind: ArtifactKind
    object_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now())
    modified_at: datetime = field(default_factory=lambda: datetime.now())
    version: int = 1
    owner: str | None = None
    tags: list[str] = field(default_factory=list)
    status: ArtifactStatus = ArtifactStatus.REGISTERED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "object_id": self.object_id,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "version": self.version,
            "owner": self.owner,
            "tags": list(self.tags),
            "status": self.status.value,
        }

    @staticmethod
    def from_dict(data: dict) -> "Artifact":
        return Artifact(
            id=data["id"],
            kind=ArtifactKind(data["kind"]),
            object_id=data["object_id"],
            content_hash=data.get("content_hash", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            version=data.get("version", 1),
            owner=data.get("owner"),
            tags=list(data.get("tags", [])),
            status=ArtifactStatus(data.get("status", ArtifactStatus.REGISTERED.value)),
        )


def register_artifact(kind: ArtifactKind, object_id: str, payload: dict, owner: str | None = None, tags: list[str] | None = None) -> Artifact:
    """`payload` is any JSON-serializable dict describing the artifact's
    current content (typically `workspace_sync.resolve_object_payload`'s
    result) -- `content_hash` is computed over it via the shared
    checksum recipe, never a second hashing scheme."""
    return Artifact(kind=kind, object_id=object_id, content_hash=compute_checksum(payload), owner=owner, tags=list(tags or []))
