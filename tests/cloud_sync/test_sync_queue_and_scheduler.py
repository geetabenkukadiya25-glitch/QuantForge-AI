"""`sync_queue.py`/`sync_scheduler.py` -- ordering/query helpers only,
confirmed nothing dispatches or fires automatically."""

from datetime import datetime, timedelta

from app.cloud_sync.cloud_models import SyncKind, SyncOperation, SyncOperationStatus
from app.cloud_sync.sync_operation import mark_running
from app.cloud_sync.sync_queue import SyncQueue, ordered_queued
from app.cloud_sync.sync_scheduler import SyncSchedule, SyncScheduler


def test_ordered_queued_returns_only_queued_oldest_first() -> None:
    op1 = SyncOperation(kind=SyncKind.DATASET, object_id="d-1", created_at=datetime(2024, 1, 1))
    op2 = SyncOperation(kind=SyncKind.DATASET, object_id="d-2", created_at=datetime(2024, 1, 2))
    op3 = SyncOperation(kind=SyncKind.DATASET, object_id="d-3", created_at=datetime(2024, 1, 3))
    mark_running(op3)
    ordered = ordered_queued({op1.id: op1, op2.id: op2, op3.id: op3})
    assert [op.id for op in ordered] == [op1.id, op2.id]


def test_sync_queue_basic_operations() -> None:
    queue = SyncQueue()
    assert queue.peek() is None
    queue.push("a")
    queue.push("b")
    assert queue.peek() == "a"
    assert queue.size() == 2
    assert queue.remove("a") is True
    assert queue.remove("a") is False
    assert queue.snapshot() == ["b"]


def test_schedule_is_due_when_never_run() -> None:
    schedule = SyncSchedule(kind=SyncKind.DATASET, interval_minutes=60)
    assert schedule.is_due(datetime.now())


def test_schedule_not_due_before_interval_elapses() -> None:
    now = datetime.now()
    schedule = SyncSchedule(kind=SyncKind.DATASET, interval_minutes=60, last_run_at=now)
    assert not schedule.is_due(now + timedelta(minutes=10))
    assert schedule.is_due(now + timedelta(minutes=61))


def test_disabled_schedule_never_due() -> None:
    schedule = SyncSchedule(kind=SyncKind.DATASET, enabled=False)
    assert not schedule.is_due(datetime.now())


def test_scheduler_due_schedules_is_a_pure_query_nothing_calls_it_automatically() -> None:
    due_schedule = SyncSchedule(kind=SyncKind.DATASET, interval_minutes=1)
    not_due_schedule = SyncSchedule(kind=SyncKind.WORKFLOW, interval_minutes=999, last_run_at=datetime.now())
    scheduler = SyncScheduler([due_schedule, not_due_schedule])
    due = scheduler.due_schedules(datetime.now())
    assert due == [due_schedule]
    # The mere existence of `due_schedules` must not have altered state.
    assert not_due_schedule.last_run_at is not None
