"""Pure `SyncOperationStatus` transition functions (Phase 17.9) -- mirrors
`app.governance.approval` exactly. Each validates the move via
`is_valid_transition` and mutates+returns the same `SyncOperation` it was
given. `SyncManager` is the only caller; it owns persistence (state save
+ history + audit) around each call. Nothing here performs I/O.
"""

from datetime import datetime

from app.cloud_sync.cloud_models import SyncOperation, SyncOperationStatus, is_valid_transition
from app.cloud_sync.exceptions import InvalidSyncTransitionError


def _transition(operation: SyncOperation, to_status: SyncOperationStatus, action: str) -> SyncOperation:
    if not is_valid_transition(operation.status, to_status):
        raise InvalidSyncTransitionError(f"Cannot {action} '{operation.object_label or operation.object_id}' from status {operation.status.value} to {to_status.value}.")
    operation.status = to_status
    return operation


def mark_running(operation: SyncOperation) -> SyncOperation:
    _transition(operation, SyncOperationStatus.RUNNING, "start")
    operation.started_at = datetime.now()
    return operation


def mark_completed(operation: SyncOperation, result_summary: str = "") -> SyncOperation:
    _transition(operation, SyncOperationStatus.COMPLETED, "complete")
    operation.completed_at = datetime.now()
    operation.result_summary = result_summary
    return operation


def mark_failed(operation: SyncOperation, error: str) -> SyncOperation:
    _transition(operation, SyncOperationStatus.FAILED, "fail")
    operation.completed_at = datetime.now()
    operation.error = error
    return operation


def cancel(operation: SyncOperation) -> SyncOperation:
    _transition(operation, SyncOperationStatus.CANCELLED, "cancel")
    operation.completed_at = datetime.now()
    return operation


def retry(operation: SyncOperation) -> SyncOperation:
    """Re-queues a CANCELLED/FAILED operation via the transient RETRY
    status, landing back on QUEUED -- a full re-attempt, never a resume
    mid-flight (see `cloud_models.py`'s documented simplification)."""
    _transition(operation, SyncOperationStatus.RETRY, "retry")
    _transition(operation, SyncOperationStatus.QUEUED, "retry")
    operation.retry_count += 1
    operation.started_at = None
    operation.completed_at = None
    operation.error = None
    return operation
