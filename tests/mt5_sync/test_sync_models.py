"""`sync_models.py` -- round-trips for every dataclass."""

from datetime import datetime, time

from app.mt5_sync.sync_models import SessionWindow, SpreadSample, SyncKind, SyncRun, SyncStatus


def test_sync_run_round_trip() -> None:
    run = SyncRun(kind=SyncKind.TICK, target="EURUSD", status=SyncStatus.COMPLETED, records_synced=10, latency_ms=1.5, completed_at=datetime(2026, 1, 1, 12, 0, 0))
    assert SyncRun.from_dict(run.to_dict()) == run


def test_sync_run_defaults() -> None:
    run = SyncRun(kind=SyncKind.SYMBOL)
    assert run.status == SyncStatus.PENDING
    assert run.records_synced == 0
    assert run.id


def test_session_window_round_trip() -> None:
    window = SessionWindow(name="London", utc_open=time(8, 0), utc_close=time(17, 0), is_active=True)
    assert SessionWindow.from_dict(window.to_dict()) == window


def test_spread_sample_round_trip() -> None:
    sample = SpreadSample(symbol="EURUSD", spread=0.0002, bid=1.1, ask=1.1002, sampled_at=datetime(2026, 1, 1, 12, 0, 0))
    assert SpreadSample.from_dict(sample.to_dict()) == sample
