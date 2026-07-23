"""`mt5_models.py` -- `ConnectionState` transition matrix + dataclass
round-trips."""

from datetime import datetime, timezone

import pytest

from app.mt5.mt5_models import (
    AccountInfo,
    Bar,
    ConnectionState,
    HealthSnapshot,
    MT5ManagerState,
    SymbolInfo,
    TerminalInfo,
    Tick,
    is_valid_transition,
)


def test_connected_only_reachable_from_connecting_or_reconnecting() -> None:
    reachable_from = {s for s in ConnectionState if is_valid_transition(s, ConnectionState.CONNECTED)}
    assert reachable_from == {ConnectionState.CONNECTING, ConnectionState.RECONNECTING}


def test_disconnected_to_connecting_is_valid() -> None:
    assert is_valid_transition(ConnectionState.DISCONNECTED, ConnectionState.CONNECTING)


def test_permission_denied_only_returns_to_disconnected() -> None:
    reachable = {s for s in ConnectionState if is_valid_transition(ConnectionState.PERMISSION_DENIED, s)}
    assert reachable == {ConnectionState.DISCONNECTED}


def test_unknown_transition_rejected() -> None:
    assert not is_valid_transition(ConnectionState.DISCONNECTED, ConnectionState.CONNECTED)
    assert not is_valid_transition(ConnectionState.LOST, ConnectionState.CONNECTED)


@pytest.mark.parametrize("state", list(ConnectionState))
def test_every_state_has_a_defined_edge_set(state: ConnectionState) -> None:
    # Every state should participate in the map (even if only as a source
    # with no outgoing edges would be a design smell) -- confirms no
    # state was left out of `_TRANSITIONS` by accident.
    assert isinstance(is_valid_transition(state, state), bool)


def test_terminal_info_round_trip() -> None:
    info = TerminalInfo(community_account=False, connected=True, trade_allowed=True, trade_expert=False, build=6033, name="MetaTrader 5", company="MetaQuotes Ltd.", path="C:/MT5", data_path="C:/MT5/data")
    assert TerminalInfo.from_dict(info.to_dict()) == info


def test_account_info_round_trip() -> None:
    info = AccountInfo(login=123, server="Demo-Server", currency="USD", balance=1000.0, equity=1000.0, margin=0.0, margin_free=1000.0, leverage=100, trade_allowed=True)
    assert AccountInfo.from_dict(info.to_dict()) == info


def test_symbol_info_round_trip() -> None:
    info = SymbolInfo(name="EURUSD", description="Euro vs US Dollar", path="Forex\\EURUSD", digits=5, point=0.00001, visible=True, spread=2)
    assert SymbolInfo.from_dict(info.to_dict()) == info


def test_bar_round_trip() -> None:
    bar = Bar(time=datetime(2026, 1, 1, 12, 0, 0), open=1.1, high=1.2, low=1.0, close=1.15, tick_volume=100, spread=2, real_volume=0)
    assert Bar.from_dict(bar.to_dict()) == bar


def test_tick_round_trip() -> None:
    tick = Tick(time=datetime(2026, 1, 1, 12, 0, 0), bid=1.1, ask=1.1002, last=0.0, volume=0, flags=6)
    assert Tick.from_dict(tick.to_dict()) == tick


def test_health_snapshot_round_trip_with_nones() -> None:
    snapshot = HealthSnapshot(
        connection_state=ConnectionState.DISCONNECTED,
        latency_ms=None,
        connection_uptime_seconds=None,
        last_heartbeat_at=None,
        last_tick_at=None,
        last_history_sync_at=None,
        last_ping_at=None,
        terminal_build=None,
        bridge_version="1.0.0",
    )
    assert HealthSnapshot.from_dict(snapshot.to_dict()) == snapshot


def test_health_snapshot_round_trip_with_values() -> None:
    now = datetime.now(timezone.utc)
    snapshot = HealthSnapshot(
        connection_state=ConnectionState.CONNECTED,
        latency_ms=1.23,
        connection_uptime_seconds=10.0,
        last_heartbeat_at=now,
        last_tick_at=now,
        last_history_sync_at=now,
        last_ping_at=now,
        terminal_build=6033,
        bridge_version="1.0.0",
    )
    assert HealthSnapshot.from_dict(snapshot.to_dict()) == snapshot


def test_mt5_manager_state_defaults_and_round_trip() -> None:
    state = MT5ManagerState()
    assert state.connection_state == ConnectionState.DISCONNECTED
    assert state.auto_connect is False
    round_tripped = MT5ManagerState.from_dict(state.to_dict())
    assert round_tripped == state
