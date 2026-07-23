"""`terminal_health.py` -- pure aggregation, no new I/O."""

from app.mt5.connection_manager import ConnectionManager
from app.mt5.mt5_models import ConnectionState
from app.mt5.terminal_health import build_health_snapshot


def test_health_snapshot_reflects_disconnected_state() -> None:
    connection = ConnectionManager()
    snapshot = build_health_snapshot(connection)
    assert snapshot.connection_state == ConnectionState.DISCONNECTED
    assert snapshot.latency_ms is None
    assert snapshot.connection_uptime_seconds is None
    assert snapshot.bridge_version
