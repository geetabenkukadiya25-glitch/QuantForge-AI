"""Data models for the Institutional Cloud Sync Foundation (Phase 17.9).
No logic beyond `to_dict`/`from_dict` and the status-transition adjacency
map -- mirrors `app.governance.governance_models` exactly. Pure metadata:
nothing here performs network I/O, and no field ever holds a credential
value.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyncOperationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    RETRY = "RETRY"


# Legal `SyncOperationStatus` transitions -- enforced by `sync_operation.py`.
# Simplification, documented: `retry()` always re-lands the operation on
# QUEUED (via the transient RETRY status) rather than resuming mid-flight,
# mirroring `WorkflowManager.retry_step`'s "a full re-run is the honest
# way to retry" reasoning from Phase 17.6.
_TRANSITIONS: dict[SyncOperationStatus, frozenset[SyncOperationStatus]] = {
    SyncOperationStatus.QUEUED: frozenset({SyncOperationStatus.RUNNING, SyncOperationStatus.CANCELLED}),
    SyncOperationStatus.RUNNING: frozenset({SyncOperationStatus.COMPLETED, SyncOperationStatus.FAILED, SyncOperationStatus.CANCELLED}),
    SyncOperationStatus.COMPLETED: frozenset(),
    SyncOperationStatus.CANCELLED: frozenset({SyncOperationStatus.RETRY}),
    SyncOperationStatus.FAILED: frozenset({SyncOperationStatus.RETRY}),
    SyncOperationStatus.RETRY: frozenset({SyncOperationStatus.QUEUED}),
}


def is_valid_transition(from_status: SyncOperationStatus, to_status: SyncOperationStatus) -> bool:
    return to_status in _TRANSITIONS.get(from_status, frozenset())


class SyncKind(str, Enum):
    DATASET = "DATASET"
    STRATEGY = "STRATEGY"
    WORKFLOW = "WORKFLOW"
    RISK_REPORT = "RISK_REPORT"
    GOVERNANCE_RECORD = "GOVERNANCE_RECORD"
    SETTINGS = "SETTINGS"
    ARTIFACT = "ARTIFACT"
    SNAPSHOT = "SNAPSHOT"


@dataclass
class SyncOperation:
    """A queued/executed (in the metadata sense only -- never a real
    network transfer) sync request. Referenced purely by
    `(kind, object_id)`, never a copy of the underlying object."""

    kind: SyncKind
    object_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    object_label: str = ""
    provider_id: str | None = None
    status: SyncOperationStatus = SyncOperationStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now())
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    retry_count: int = 0
    result_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "object_id": self.object_id,
            "object_label": self.object_label,
            "provider_id": self.provider_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "result_summary": self.result_summary,
        }

    @staticmethod
    def from_dict(data: dict) -> "SyncOperation":
        return SyncOperation(
            id=data["id"],
            kind=SyncKind(data["kind"]),
            object_id=data["object_id"],
            object_label=data.get("object_label", ""),
            provider_id=data.get("provider_id"),
            status=SyncOperationStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            result_summary=data.get("result_summary", ""),
        )


@dataclass
class CloudSyncManagerState:
    """The persisted state: every `SyncOperation`/`Artifact`/`Snapshot`
    plus the active `SyncPolicy`. Mirrors `GovernanceManagerState`'s
    shape; nested-type imports are local to `to_dict`/`from_dict` to keep
    this module free of a hard import-order dependency on `artifact.py`/
    `snapshot.py`/`sync_policy.py`."""

    operations: dict[str, SyncOperation] = field(default_factory=dict)
    artifacts: dict[str, object] = field(default_factory=dict)  # values are `artifact.Artifact`
    snapshots: dict[str, object] = field(default_factory=dict)  # values are `snapshot.Snapshot`
    policy: object | None = None  # `sync_policy.SyncPolicy`

    def to_dict(self) -> dict:
        from app.cloud_sync.sync_policy import SyncPolicy

        return {
            "operations": {k: v.to_dict() for k, v in self.operations.items()},
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()},
            "snapshots": {k: v.to_dict() for k, v in self.snapshots.items()},
            "policy": self.policy.to_dict() if self.policy is not None else SyncPolicy().to_dict(),
        }

    @staticmethod
    def from_dict(data: dict) -> "CloudSyncManagerState":
        from app.cloud_sync.artifact import Artifact
        from app.cloud_sync.snapshot import Snapshot
        from app.cloud_sync.sync_policy import SyncPolicy

        policy_data = data.get("policy")
        return CloudSyncManagerState(
            operations={k: SyncOperation.from_dict(v) for k, v in data.get("operations", {}).items()},
            artifacts={k: Artifact.from_dict(v) for k, v in data.get("artifacts", {}).items()},
            snapshots={k: Snapshot.from_dict(v) for k, v in data.get("snapshots", {}).items()},
            policy=SyncPolicy.from_dict(policy_data) if policy_data is not None else SyncPolicy(),
        )
