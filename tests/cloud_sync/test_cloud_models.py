"""`cloud_models.py` -- round-trip serialization and the
`SyncOperationStatus` transition matrix."""

from app.cloud_sync.cloud_models import CloudSyncManagerState, SyncKind, SyncOperation, SyncOperationStatus, is_valid_transition


def test_sync_operation_round_trip() -> None:
    op = SyncOperation(kind=SyncKind.DATASET, object_id="d-1", object_label="Dataset One", retry_count=2)
    restored = SyncOperation.from_dict(op.to_dict())
    assert restored.id == op.id
    assert restored.kind == SyncKind.DATASET
    assert restored.status == SyncOperationStatus.QUEUED
    assert restored.retry_count == 2


def test_manager_state_round_trip() -> None:
    op = SyncOperation(kind=SyncKind.WORKFLOW, object_id="w-1")
    state = CloudSyncManagerState(operations={op.id: op})
    restored = CloudSyncManagerState.from_dict(state.to_dict())
    assert op.id in restored.operations
    assert restored.policy is not None


def test_valid_transitions() -> None:
    assert is_valid_transition(SyncOperationStatus.QUEUED, SyncOperationStatus.RUNNING)
    assert is_valid_transition(SyncOperationStatus.RUNNING, SyncOperationStatus.COMPLETED)
    assert is_valid_transition(SyncOperationStatus.RUNNING, SyncOperationStatus.FAILED)
    assert is_valid_transition(SyncOperationStatus.FAILED, SyncOperationStatus.RETRY)
    assert is_valid_transition(SyncOperationStatus.RETRY, SyncOperationStatus.QUEUED)


def test_invalid_transitions_rejected() -> None:
    assert not is_valid_transition(SyncOperationStatus.COMPLETED, SyncOperationStatus.RUNNING)
    assert not is_valid_transition(SyncOperationStatus.QUEUED, SyncOperationStatus.COMPLETED)
    assert not is_valid_transition(SyncOperationStatus.CANCELLED, SyncOperationStatus.RUNNING)
