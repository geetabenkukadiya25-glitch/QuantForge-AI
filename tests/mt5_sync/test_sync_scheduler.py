"""`sync_scheduler.py` -- pure query surface, nothing fires
automatically."""

from datetime import datetime, timedelta

from app.mt5_sync.sync_models import SyncKind
from app.mt5_sync.sync_scheduler import SyncSchedule, SyncScheduler


def test_new_schedule_with_no_last_run_is_due() -> None:
    schedule = SyncSchedule(kind=SyncKind.TICK, interval_minutes=15)
    assert schedule.is_due(datetime.now()) is True


def test_schedule_not_due_before_interval_elapses() -> None:
    now = datetime.now()
    schedule = SyncSchedule(kind=SyncKind.TICK, interval_minutes=15, last_run_at=now)
    assert schedule.is_due(now + timedelta(minutes=5)) is False


def test_schedule_due_after_interval_elapses() -> None:
    now = datetime.now()
    schedule = SyncSchedule(kind=SyncKind.TICK, interval_minutes=15, last_run_at=now)
    assert schedule.is_due(now + timedelta(minutes=20)) is True


def test_disabled_schedule_never_due() -> None:
    schedule = SyncSchedule(kind=SyncKind.TICK, interval_minutes=15, enabled=False)
    assert schedule.is_due(datetime.now()) is False


def test_schedule_round_trip() -> None:
    schedule = SyncSchedule(kind=SyncKind.BAR, interval_minutes=30, target="EURUSD")
    assert SyncSchedule.from_dict(schedule.to_dict()) == schedule


def test_scheduler_due_schedules_is_pure_query() -> None:
    scheduler = SyncScheduler()
    scheduler.add(SyncSchedule(kind=SyncKind.TICK, interval_minutes=5))
    scheduler.add(SyncSchedule(kind=SyncKind.BAR, interval_minutes=5, enabled=False))
    due = scheduler.due_schedules(datetime.now())
    assert len(due) == 1
    assert due[0].kind == SyncKind.TICK
    # Calling it again doesn't change anything -- no side effects, no timer.
    assert scheduler.due_schedules(datetime.now()) == due
    assert len(scheduler.list_schedules()) == 2
