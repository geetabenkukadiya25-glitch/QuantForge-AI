"""`connection_manager.py` -- state machine + real connect/disconnect
against whatever MT5 installation the test environment actually has.
Guarded by `requires_real_terminal` so the suite passes identically
with or without a live terminal -- "never fabricate connection" is
verified here directly: failure paths never claim CONNECTED."""

import pytest

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import InvalidConnectionTransitionError, MT5ConnectionError, MT5NotInstalledError
from app.mt5.mt5_models import ConnectionState
from tests.mt5.conftest import requires_real_terminal


def test_import_mt5_raises_domain_error_not_import_error(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "MetaTrader5":
            raise ImportError("simulated missing package")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(MT5NotInstalledError):
        import_mt5()


def test_new_manager_starts_disconnected() -> None:
    manager = ConnectionManager()
    assert manager.state == ConnectionState.DISCONNECTED
    assert manager.uptime_seconds() is None
    assert manager.last_latency_ms() is None


def test_ping_before_connect_raises() -> None:
    manager = ConnectionManager()
    with pytest.raises(MT5ConnectionError):
        manager.ping()


def test_disconnect_when_already_disconnected_is_a_noop() -> None:
    manager = ConnectionManager()
    assert manager.disconnect() == ConnectionState.DISCONNECTED


def test_reconnect_from_disconnected_does_not_go_through_reconnecting_state() -> None:
    # `reconnect()` only pre-transitions LOST -> RECONNECTING; called
    # from any other state it just delegates straight to `connect()`.
    manager = ConnectionManager()
    manager.reconnect()
    assert manager.state != ConnectionState.RECONNECTING


def test_manual_invalid_transition_raises() -> None:
    manager = ConnectionManager()
    with pytest.raises(InvalidConnectionTransitionError):
        manager._transition(ConnectionState.CONNECTED)  # DISCONNECTED -> CONNECTED is illegal


@requires_real_terminal
def test_real_connect_reaches_connected_and_disconnect_returns_to_disconnected() -> None:
    manager = ConnectionManager()
    state = manager.connect()
    assert state == ConnectionState.CONNECTED
    assert manager.uptime_seconds() is not None
    latency = manager.ping()
    assert latency >= 0
    assert manager.disconnect() == ConnectionState.DISCONNECTED


def test_connect_without_real_terminal_never_fabricates_connected(has_real_terminal) -> None:
    if has_real_terminal:
        pytest.skip("A real terminal is available -- this test only verifies the no-terminal degrade path.")
    manager = ConnectionManager()
    state = manager.connect()
    assert state != ConnectionState.CONNECTED
    manager.disconnect()
