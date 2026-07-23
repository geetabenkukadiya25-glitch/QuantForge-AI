"""`MT5Manager` integration -- full lifecycle against whatever the real
environment provides (real terminal if present, honest degradation if
not), settings persistence, audit trail, and `JobManager`-submitted
history/tick sync/diagnostics jobs. Mirrors the "unchanged"/deadline-
polling integration-test style used throughout Phases 17.8/17.9/18.8.
"""

import time
from datetime import datetime, timedelta

import pytest

from app.job_manager.job_state import JobState, is_terminal
from app.mt5.audit import MT5AuditEventType
from app.mt5.mt5_models import ConnectionState
from tests.mt5.conftest import requires_real_terminal


def _wait_for_terminal(job, deadline_seconds: float = 15.0):
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if is_terminal(job.state):
            return job
        time.sleep(0.05)
    return job


def test_settings_persist_across_manager_instances(mt5_manager, tmp_path) -> None:
    mt5_manager.update_settings(auto_connect=True, retry_interval_seconds=60, terminal_path_override="C:/custom/terminal64.exe")
    reloaded_state = mt5_manager._state_dir  # same dir, fresh instance
    from app.mt5.terminal_manager import MT5Manager

    second = MT5Manager(state_dir=reloaded_state)
    settings = second.get_settings()
    assert settings.auto_connect is True
    assert settings.retry_interval_seconds == 60
    assert settings.terminal_path_override == "C:/custom/terminal64.exe"


def test_settings_update_is_audited(mt5_manager) -> None:
    mt5_manager.update_settings(auto_connect=True)
    kinds = {e.event_type for e in mt5_manager.list_audit_events()}
    assert MT5AuditEventType.SETTINGS_UPDATED in kinds


def test_connect_disconnect_lifecycle_is_audited(mt5_manager) -> None:
    mt5_manager.connect()
    mt5_manager.disconnect()
    kinds = [e.event_type for e in mt5_manager.list_audit_events()]
    assert MT5AuditEventType.CONNECT_ATTEMPTED in kinds
    assert MT5AuditEventType.DISCONNECTED in kinds


def test_data_access_before_connect_raises_domain_errors(mt5_manager) -> None:
    from app.mt5.exceptions import MT5ConnectionError

    with pytest.raises(MT5ConnectionError):
        mt5_manager.get_account_info()
    with pytest.raises(MT5ConnectionError):
        mt5_manager.get_terminal_info()


def test_run_diagnostics_never_raises(mt5_manager) -> None:
    report = mt5_manager.run_diagnostics()
    assert len(report.steps) >= 2


@requires_real_terminal
def test_full_real_lifecycle_connect_read_disconnect(mt5_manager) -> None:
    state = mt5_manager.connect()
    assert state == ConnectionState.CONNECTED

    terminal = mt5_manager.get_terminal_info()
    assert terminal.connected is True

    account = mt5_manager.get_account_info()
    assert account.login > 0

    symbols = mt5_manager.list_symbols()
    assert len(symbols) > 0

    health = mt5_manager.get_health_snapshot()
    assert health.connection_state == ConnectionState.CONNECTED
    assert health.terminal_build == terminal.build

    mt5_manager.disconnect()
    assert mt5_manager.connection_state == ConnectionState.DISCONNECTED


@requires_real_terminal
def test_submit_history_sync_via_job_manager(mt5_manager) -> None:
    mt5_manager.connect()
    symbols = [s for s in mt5_manager.list_symbols() if s.visible]
    if not symbols:
        mt5_manager.disconnect()
        pytest.skip("No visible symbols on this terminal's Market Watch.")

    now = datetime.now()
    job = mt5_manager.submit_history_sync(symbols[0].name, "H1", now - timedelta(days=2), now, owner_page="test")
    job = _wait_for_terminal(job)
    assert job.state == JobState.COMPLETED
    assert isinstance(job.result, list)

    kinds = [e.event_type for e in mt5_manager.list_audit_events()]
    assert MT5AuditEventType.HISTORY_SYNCED in kinds

    mt5_manager.disconnect()


@requires_real_terminal
def test_submit_diagnostics_via_job_manager(mt5_manager) -> None:
    job = mt5_manager.submit_diagnostics(owner_page="test")
    job = _wait_for_terminal(job)
    assert job.state == JobState.COMPLETED
    assert job.result is not None
    assert job.result.steps
