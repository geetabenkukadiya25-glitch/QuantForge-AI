"""`SyncManager` integration -- queues sync operations for REAL,
tmp-scoped `Workflow`/`DatasetRecord` objects, transitions them through
their full lifecycle, and confirms their own managers are completely
untouched afterward -- the "unchanged" assertion style used throughout
Phase 17.8's integration tests. No network I/O, no `JobManager` usage
anywhere in this file's target code.
"""

from app.cloud_sync.artifact import ArtifactKind
from app.cloud_sync.cloud_models import SyncOperationStatus
from app.cloud_sync.exceptions import InvalidSyncTransitionError, OperationNotFoundError
from app.cloud_sync.snapshot import SnapshotKind

import pytest

VALID_CSV = (
    b"Date,Time,Open,High,Low,Close,Volume,Spread\n"
    b"2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    b"2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
)


@pytest.fixture
def real_workflow(tmp_path, monkeypatch):
    from app.workflow.workflow_manager import WorkflowManager

    manager = WorkflowManager(state_dir=tmp_path / "wf_state")
    monkeypatch.setattr("app.workflow.get_workflow_manager", lambda: manager)
    workflow = manager.create(name="Sync Target Workflow", author="alice")
    return manager, workflow


@pytest.fixture
def real_dataset(tmp_path):
    from app.dataset_manager import DatasetManager

    manager = DatasetManager(registry_dir=tmp_path / "dm_registry", state_dir=tmp_path / "dm_state")
    record = manager.import_dataset_from_bytes(VALID_CSV, filename="EURUSD_H1.csv", display_name="EURUSD H1")
    return manager, record


def test_sync_workflow_full_lifecycle_leaves_workflow_untouched(sync_manager, real_workflow) -> None:
    workflow_manager, workflow = real_workflow
    op = sync_manager.sync_workflow(workflow.id)
    assert op.status == SyncOperationStatus.QUEUED
    assert op.object_label == "Sync Target Workflow"  # resolved via workspace_sync, not fabricated

    sync_manager.mark_running(op.id)
    sync_manager.mark_completed(op.id, "metadata sync only -- no real transfer")
    finished = sync_manager.get_operation(op.id)
    assert finished.status == SyncOperationStatus.COMPLETED

    # The governed workflow's own state is completely untouched.
    unchanged = workflow_manager.get(workflow.id)
    assert unchanged.status.value == "DRAFT"
    assert unchanged.name == "Sync Target Workflow"


def test_sync_dataset_cancel_and_retry(sync_manager, real_dataset) -> None:
    # `DatasetManager` (unlike `WorkflowManager`) has no process-wide
    # singleton -- `workspace_sync.resolve_object_label` always
    # instantiates a fresh one against the REAL global paths, so it
    # can't see this test's tmp-scoped dataset and falls back to
    # `object_id` as the label. Same documented limitation as Phase
    # 17.8's governance integration tests.
    dataset_manager, dataset = real_dataset
    op = sync_manager.sync_dataset(dataset.id)
    assert op.object_label == dataset.id

    sync_manager.cancel(op.id)
    assert sync_manager.get_operation(op.id).status == SyncOperationStatus.CANCELLED

    sync_manager.retry(op.id)
    retried = sync_manager.get_operation(op.id)
    assert retried.status == SyncOperationStatus.QUEUED
    assert retried.retry_count == 1

    # Dataset Manager's own record is untouched.
    assert dataset_manager.get(dataset.id).display_name == "EURUSD H1"


def test_invalid_transition_raises(sync_manager, real_dataset) -> None:
    _, dataset = real_dataset
    op = sync_manager.sync_dataset(dataset.id)
    with pytest.raises(InvalidSyncTransitionError):
        sync_manager.mark_completed(op.id)  # QUEUED -> COMPLETED is not legal


def test_unknown_operation_raises(sync_manager) -> None:
    with pytest.raises(OperationNotFoundError):
        sync_manager.get_operation("nonexistent-id")
    with pytest.raises(OperationNotFoundError):
        sync_manager.mark_running("nonexistent-id")


def test_register_artifact_and_sync_it(sync_manager, real_dataset) -> None:
    _, dataset = real_dataset
    artifact = sync_manager.register_artifact(ArtifactKind.DATASET, dataset.id)
    assert artifact.content_hash

    op = sync_manager.sync_artifact(artifact.id)
    assert op.object_id == artifact.id


def test_create_snapshot_and_sync_it(sync_manager, real_workflow) -> None:
    _, workflow = real_workflow
    snapshot = sync_manager.create_snapshot(SnapshotKind.WORKSPACE, "checkpoint", [workflow.id])
    op = sync_manager.sync_snapshot(snapshot.id)
    assert op.object_id == snapshot.id


def test_policy_update_and_audit(sync_manager) -> None:
    sync_manager.update_policy(auto_retry_enabled=True, max_retry_count=10)
    policy = sync_manager.get_policy()
    assert policy.auto_retry_enabled is True
    assert policy.max_retry_count == 10
    kinds = {e.event_type.value for e in sync_manager.list_audit_events()}
    assert "POLICY_UPDATED" in kinds


def test_audit_and_history_populated_by_real_actions(sync_manager, real_dataset) -> None:
    import time

    _, dataset = real_dataset
    op = sync_manager.sync_dataset(dataset.id)
    time.sleep(0.01)
    sync_manager.mark_running(op.id)
    time.sleep(0.01)
    sync_manager.mark_completed(op.id)

    audit_kinds = {e.event_type.value for e in sync_manager.list_audit_events(op.id)}
    assert {"CREATED", "RUNNING", "COMPLETED"}.issubset(audit_kinds)

    history = sync_manager.list_history(op.id)
    assert len(history) >= 3
    assert history[0].status == SyncOperationStatus.COMPLETED  # newest first


def test_list_providers_none_actually_connectable(sync_manager) -> None:
    providers = sync_manager.list_providers()
    assert len(providers) == 6
    for descriptor in providers:
        provider = descriptor.provider_cls()
        with pytest.raises(NotImplementedError):
            provider.connect()
