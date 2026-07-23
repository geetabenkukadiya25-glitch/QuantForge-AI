"""`SyncEngineManager` integration -- full surface against the real,
already-connected terminal (real symbol/tick/bar/market-watch/market-
book sync, real spread sample, real session computation, statistics/
health counters incrementing, audit events recorded, one job submitted
via `JobManager` under `JobCategory.MT5_SYNC`)."""

import time

import pytest

from app.job_manager.job_state import JobState, is_terminal
from app.mt5.mt5_models import ConnectionState
from app.mt5_sync.audit import SyncAuditEventType
from app.mt5_sync.sync_models import SyncKind, SyncStatus
from tests.mt5_sync.conftest import requires_real_terminal


def _wait_for_terminal(job, deadline_seconds: float = 15.0):
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if is_terminal(job.state):
            return job
        time.sleep(0.05)
    return job


def test_sync_symbols_disconnected_updates_statistics_and_audit(sync_manager) -> None:
    run = sync_manager.sync_symbols()
    assert run.status == SyncStatus.FAILED
    stats = sync_manager.get_statistics()
    assert stats.total_runs == 1
    assert stats.failure_count == 1
    kinds = [e.event_type for e in sync_manager.list_audit_events()]
    assert SyncAuditEventType.SYNC_FAILED in kinds


def test_compute_sessions_updates_statistics(sync_manager) -> None:
    windows = sync_manager.compute_sessions()
    assert len(windows) == 4
    stats = sync_manager.get_statistics()
    assert stats.runs_by_kind.get("SESSION") == 1


def test_health_reflects_connection_state(sync_manager, mt5_manager) -> None:
    health = sync_manager.get_health()
    assert health.connection_state == mt5_manager.connection_state.value


def test_submit_sync_job_unsupported_kind_raises(sync_manager) -> None:
    from app.mt5_sync.exceptions import SyncTargetError

    with pytest.raises(SyncTargetError):
        sync_manager.submit_sync_job(SyncKind.SPREAD, owner_page="test")


@requires_real_terminal
def test_full_real_sync_cycle(sync_manager, mt5_manager) -> None:
    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        symbol_run = sync_manager.sync_symbols()
        assert symbol_run.status == SyncStatus.COMPLETED

        symbols = [s for s in mt5_manager.list_symbols() if s.visible]
        if not symbols:
            pytest.skip("No visible symbols on this terminal's Market Watch.")
        symbol = symbols[0].name

        tick_run = sync_manager.sync_ticks(symbol, 10)
        bar_run = sync_manager.sync_bars(symbol, "H1", 10)
        watch_run = sync_manager.sync_market_watch([symbol])
        book_run = sync_manager.sync_market_book(symbol)
        spread_sample = sync_manager.sample_spread(symbol)
        sessions = sync_manager.compute_sessions()

        assert tick_run.status == SyncStatus.COMPLETED
        assert bar_run.status == SyncStatus.COMPLETED
        assert watch_run.status == SyncStatus.COMPLETED
        assert book_run.status == SyncStatus.COMPLETED
        assert spread_sample.spread >= 0
        assert len(sessions) == 4

        stats = sync_manager.get_statistics()
        assert stats.total_runs == 7  # symbol, tick, bar, watch, book, spread, session
        assert stats.failure_count == 0

        health = sync_manager.get_health()
        assert health.overall_status == "healthy"
        assert health.connection_state == "CONNECTED"

        report = sync_manager.run_diagnostics()
        assert report.all_passed

        document = sync_manager.export_via_bridge(history_symbol=symbol, tick_symbol=symbol)
        assert document["checksum"]

        job = sync_manager.submit_sync_job(SyncKind.TICK, owner_page="test", symbol=symbol, count=5)
        job = _wait_for_terminal(job)
        assert job.state == JobState.COMPLETED
        assert job.result.status == SyncStatus.COMPLETED
    finally:
        mt5_manager.disconnect()
