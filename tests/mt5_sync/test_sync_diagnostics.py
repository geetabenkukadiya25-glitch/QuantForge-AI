"""`sync_diagnostics.py` -- composes `MT5Manager.run_diagnostics()`
(reused, not duplicated) with additional sync-specific steps."""

from app.mt5_sync.sync_diagnostics import run_sync_diagnostics
from app.mt5_sync.sync_statistics import SyncStatistics


def test_run_sync_diagnostics_includes_base_and_sync_steps(mt5_manager) -> None:
    report = run_sync_diagnostics(mt5_manager, SyncStatistics())
    names = [s.name for s in report.steps]
    # Base connection checks (from MT5Manager.run_diagnostics()) are present...
    assert "MetaTrader5 package import" in names
    assert "Terminal discovery" in names
    # ...and the sync-layer-specific steps are appended on top.
    assert "Recent sync success rate" in names
    assert "Scheduler due count" in names
    assert "Diagnostics timestamp" in names


def test_run_sync_diagnostics_no_runs_yet_is_informational_not_failing(mt5_manager) -> None:
    report = run_sync_diagnostics(mt5_manager, SyncStatistics())
    success_step = next(s for s in report.steps if s.name == "Recent sync success rate")
    assert success_step.passed is True
    assert "No sync runs recorded yet" in success_step.detail


def test_run_sync_diagnostics_reflects_due_schedule_count(mt5_manager) -> None:
    report = run_sync_diagnostics(mt5_manager, SyncStatistics(), due_schedule_count=3)
    step = next(s for s in report.steps if s.name == "Scheduler due count")
    assert "3 schedule(s)" in step.detail
