"""`SyncManager` orchestrator (Phase 17.9) -- CRUD over `SyncOperation`/
`Artifact`/`Snapshot` records (mirrors `GovernanceManager`'s JSON-state
pattern), the 5 status-transition actions from `sync_operation.py`,
provider registration (delegates to `provider_registry.py`), policy
CRUD, and conflict recording. NO `JobManager` import anywhere in this
file -- every "sync" action only ever creates or transitions a metadata
record; there is no real work to dispatch, no worker thread, no network
call. Never mutates any of the 6 real managers it reads from via
`workspace_sync.py` -- every action here only ever reads a governed
object by id and writes this module's own separate state.
"""

import dataclasses
import json
import threading
from pathlib import Path

from app.cloud_sync import sync_operation
from app.cloud_sync import workspace_sync
from app.cloud_sync.artifact import Artifact, ArtifactKind, register_artifact
from app.cloud_sync.cloud_models import CloudSyncManagerState, SyncKind, SyncOperation, SyncOperationStatus
from app.cloud_sync.exceptions import ArtifactNotFoundError, OperationNotFoundError, SnapshotNotFoundError
from app.cloud_sync.provider_registry import DEFAULT_REGISTRY, ProviderRegistry
from app.cloud_sync.snapshot import Snapshot, SnapshotKind, create_snapshot
from app.cloud_sync.sync_audit import SyncAuditEventType, SyncAuditLogStore
from app.cloud_sync.sync_conflict import ConflictKind, ConflictResolutionPolicy, SyncConflict, resolve_conflict
from app.cloud_sync.sync_history import SyncHistoryStore
from app.cloud_sync.sync_policy import SyncPolicy
from app.config.paths import get_paths
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DECISION_TO_AUDIT: dict[str, SyncAuditEventType] = {
    "mark_running": SyncAuditEventType.RUNNING,
    "mark_completed": SyncAuditEventType.COMPLETED,
    "mark_failed": SyncAuditEventType.FAILED,
    "cancel": SyncAuditEventType.CANCELLED,
    "retry": SyncAuditEventType.RETRIED,
}


class SyncManager:
    def __init__(self, state_dir: Path | None = None, registry: ProviderRegistry | None = None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.cloud_sync_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._history = SyncHistoryStore(self._state_dir)
        self._audit_log = SyncAuditLogStore(self._state_dir)
        self._registry = registry or DEFAULT_REGISTRY
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Sync entry points -- each creates one QUEUED SyncOperation.
    # Never performs any real transfer; only metadata is created.
    # ------------------------------------------------------------------

    def _enqueue(self, kind: SyncKind, object_id: str, provider_id: str | None = None) -> SyncOperation:
        label = workspace_sync.resolve_object_label(kind, object_id) or object_id
        operation = SyncOperation(kind=kind, object_id=object_id, object_label=label, provider_id=provider_id)
        with self._lock:
            state = self._load_state()
            state.operations[operation.id] = operation
            self._save_state(state)
        self._audit_log.record(SyncAuditEventType.CREATED, operation.id)
        self._history.record(operation)
        return operation

    def sync_dataset(self, dataset_id: str, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.DATASET, dataset_id, provider_id)

    def sync_strategy(self, strategy_path: str, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.STRATEGY, strategy_path, provider_id)

    def sync_workflow(self, workflow_id: str, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.WORKFLOW, workflow_id, provider_id)

    def sync_risk_report(self, report_id: str, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.RISK_REPORT, report_id, provider_id)

    def sync_governance_record(self, record_id: str, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.GOVERNANCE_RECORD, record_id, provider_id)

    def sync_settings(self, provider_id: str | None = None) -> SyncOperation:
        return self._enqueue(SyncKind.SETTINGS, "settings", provider_id)

    def sync_artifact(self, artifact_id: str, provider_id: str | None = None) -> SyncOperation:
        self.get_artifact(artifact_id)  # raises ArtifactNotFoundError if unknown
        return self._enqueue(SyncKind.ARTIFACT, artifact_id, provider_id)

    def sync_snapshot(self, snapshot_id: str, provider_id: str | None = None) -> SyncOperation:
        self.get_snapshot(snapshot_id)  # raises SnapshotNotFoundError if unknown
        return self._enqueue(SyncKind.SNAPSHOT, snapshot_id, provider_id)

    # ------------------------------------------------------------------
    # Operation CRUD / transitions
    # ------------------------------------------------------------------

    def get_operation(self, operation_id: str) -> SyncOperation:
        state = self._load_state()
        operation = state.operations.get(operation_id)
        if operation is None:
            raise OperationNotFoundError(f"No sync operation with id '{operation_id}'.")
        return operation

    def list_operations(self, status: SyncOperationStatus | None = None, kind: SyncKind | None = None) -> list[SyncOperation]:
        state = self._load_state()
        operations = list(state.operations.values())
        if status is not None:
            operations = [o for o in operations if o.status == status]
        if kind is not None:
            operations = [o for o in operations if o.kind == kind]
        operations.sort(key=lambda o: o.created_at, reverse=True)
        return operations

    def _apply_action(self, operation_id: str, action: str, *args) -> SyncOperation:
        transition_fn = getattr(sync_operation, action)
        with self._lock:
            state = self._load_state()
            operation = state.operations.get(operation_id)
            if operation is None:
                raise OperationNotFoundError(f"No sync operation with id '{operation_id}'.")
            transition_fn(operation, *args)
            self._save_state(state)
        self._audit_log.record(_DECISION_TO_AUDIT[action], operation_id)
        self._history.record(dataclasses.replace(operation))
        return operation

    def mark_running(self, operation_id: str) -> SyncOperation:
        return self._apply_action(operation_id, "mark_running")

    def mark_completed(self, operation_id: str, result_summary: str = "") -> SyncOperation:
        return self._apply_action(operation_id, "mark_completed", result_summary)

    def mark_failed(self, operation_id: str, error: str) -> SyncOperation:
        return self._apply_action(operation_id, "mark_failed", error)

    def cancel(self, operation_id: str) -> SyncOperation:
        return self._apply_action(operation_id, "cancel")

    def retry(self, operation_id: str) -> SyncOperation:
        return self._apply_action(operation_id, "retry")

    # ------------------------------------------------------------------
    # Providers (registration only -- see provider_registry.py)
    # ------------------------------------------------------------------

    def list_providers(self):
        return self._registry.list_providers()

    def get_provider(self, provider_id: str):
        return self._registry.get(provider_id)

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def register_artifact(self, kind: ArtifactKind, object_id: str, owner: str | None = None, tags: list[str] | None = None) -> Artifact:
        payload = workspace_sync.resolve_object_payload(_artifact_kind_to_sync_kind(kind), object_id) or {"object_id": object_id}
        artifact = register_artifact(kind, object_id, payload, owner=owner, tags=tags)
        with self._lock:
            state = self._load_state()
            state.artifacts[artifact.id] = artifact
            self._save_state(state)
        self._audit_log.record(SyncAuditEventType.ARTIFACT_REGISTERED, artifact.id)
        return artifact

    def get_artifact(self, artifact_id: str) -> Artifact:
        state = self._load_state()
        artifact = state.artifacts.get(artifact_id)
        if artifact is None:
            raise ArtifactNotFoundError(f"No artifact with id '{artifact_id}'.")
        return artifact

    def list_artifacts(self) -> list[Artifact]:
        return sorted(self._load_state().artifacts.values(), key=lambda a: a.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def create_snapshot(self, kind: SnapshotKind, label: str, object_refs: list[str], notes: str = "") -> Snapshot:
        snapshot = create_snapshot(kind, label, object_refs, notes)
        with self._lock:
            state = self._load_state()
            state.snapshots[snapshot.id] = snapshot
            self._save_state(state)
        self._audit_log.record(SyncAuditEventType.SNAPSHOT_CREATED, snapshot.id)
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Snapshot:
        state = self._load_state()
        snapshot = state.snapshots.get(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFoundError(f"No snapshot with id '{snapshot_id}'.")
        return snapshot

    def list_snapshots(self) -> list[Snapshot]:
        return sorted(self._load_state().snapshots.values(), key=lambda s: s.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def get_policy(self) -> SyncPolicy:
        return self._load_state().policy or SyncPolicy()

    def update_policy(self, **fields) -> SyncPolicy:
        with self._lock:
            state = self._load_state()
            policy = state.policy or SyncPolicy()
            for key, value in fields.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            state.policy = policy
            self._save_state(state)
        self._audit_log.record(SyncAuditEventType.POLICY_UPDATED, "policy")
        return policy

    # ------------------------------------------------------------------
    # Conflicts -- recording and resolution are both explicit, never automatic.
    # ------------------------------------------------------------------

    def record_conflict(self, operation_id: str, artifact_id: str, kind: ConflictKind, local_hash: str | None = None, remote_hash: str | None = None) -> SyncConflict:
        conflict = SyncConflict(operation_id=operation_id, artifact_id=artifact_id, kind=kind, local_hash=local_hash, remote_hash=remote_hash)
        self._audit_log.record(SyncAuditEventType.CONFLICT_DETECTED, conflict.id)
        return conflict

    def resolve(self, conflict: SyncConflict, resolution: ConflictResolutionPolicy, notes: str = "") -> SyncConflict:
        resolved = resolve_conflict(conflict, resolution, notes)
        self._audit_log.record(SyncAuditEventType.CONFLICT_RESOLVED, resolved.id)
        return resolved

    # ------------------------------------------------------------------
    # Audit / history
    # ------------------------------------------------------------------

    def list_audit_events(self, key: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=key, limit=limit)

    def list_history(self, operation_id: str | None = None, limit: int = 200):
        return self._history.list_records(operation_id=operation_id, limit=limit)

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _state_file(self) -> Path:
        return self._state_dir / "cloud_sync_state.json"

    def _load_state(self) -> CloudSyncManagerState:
        file = self._state_file()
        if not file.exists():
            return CloudSyncManagerState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Cloud Sync manager state file is unreadable; starting fresh.")
            return CloudSyncManagerState()
        return CloudSyncManagerState.from_dict(data)

    def _save_state(self, state: CloudSyncManagerState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def _artifact_kind_to_sync_kind(kind: ArtifactKind) -> SyncKind:
    mapping = {
        ArtifactKind.DATASET: SyncKind.DATASET,
        ArtifactKind.STRATEGY: SyncKind.STRATEGY,
        ArtifactKind.WORKFLOW: SyncKind.WORKFLOW,
        ArtifactKind.RISK_REPORT: SyncKind.RISK_REPORT,
        ArtifactKind.GOVERNANCE_REPORT: SyncKind.GOVERNANCE_RECORD,
    }
    return mapping.get(kind, SyncKind.ARTIFACT)
