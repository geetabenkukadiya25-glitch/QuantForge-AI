"""`sync_operation.py` -- every transition function, including invalid
transitions being rejected."""

import pytest

from app.cloud_sync.cloud_models import SyncKind, SyncOperation, SyncOperationStatus
from app.cloud_sync.exceptions import InvalidSyncTransitionError
from app.cloud_sync.sync_operation import cancel, mark_completed, mark_failed, mark_running, retry


def _op() -> SyncOperation:
    return SyncOperation(kind=SyncKind.DATASET, object_id="d-1")


def test_mark_running_sets_started_at() -> None:
    op = _op()
    mark_running(op)
    assert op.status == SyncOperationStatus.RUNNING
    assert op.started_at is not None


def test_mark_completed_requires_running() -> None:
    op = _op()
    with pytest.raises(InvalidSyncTransitionError):
        mark_completed(op)
    mark_running(op)
    mark_completed(op, "done")
    assert op.status == SyncOperationStatus.COMPLETED
    assert op.result_summary == "done"


def test_mark_failed_records_error() -> None:
    op = _op()
    mark_running(op)
    mark_failed(op, "boom")
    assert op.status == SyncOperationStatus.FAILED
    assert op.error == "boom"


def test_cancel_from_queued() -> None:
    op = _op()
    cancel(op)
    assert op.status == SyncOperationStatus.CANCELLED


def test_retry_returns_to_queued_and_clears_error() -> None:
    op = _op()
    mark_running(op)
    mark_failed(op, "boom")
    retry(op)
    assert op.status == SyncOperationStatus.QUEUED
    assert op.retry_count == 1
    assert op.error is None
    assert op.started_at is None
    assert op.completed_at is None


def test_retry_from_completed_rejected() -> None:
    op = _op()
    mark_running(op)
    mark_completed(op)
    with pytest.raises(InvalidSyncTransitionError):
        retry(op)
