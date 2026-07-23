"""`diagnostics.py` -- always returns a full report, never raises past
the function boundary."""

from app.mt5.connection_manager import ConnectionManager
from app.mt5.diagnostics import run_diagnostics


def test_run_diagnostics_never_raises_and_returns_steps() -> None:
    connection = ConnectionManager()
    report = run_diagnostics(connection)
    assert len(report.steps) >= 2
    names = [s.name for s in report.steps]
    assert "MetaTrader5 package import" in names
    assert "Terminal discovery" in names


def test_all_passed_reflects_step_results() -> None:
    connection = ConnectionManager()
    report = run_diagnostics(connection)
    assert report.all_passed == all(s.passed for s in report.steps)
