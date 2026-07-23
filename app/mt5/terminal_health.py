"""Aggregates a `HealthSnapshot` from the other managers' already-tracked
state (Phase 19.0) -- pure aggregation, no new I/O beyond an optional
fresh `ping()` the caller can trigger separately via `connection_manager`.
"""

from datetime import datetime, timezone

from app.mt5.connection_manager import ConnectionManager
from app.mt5.mt5_models import HealthSnapshot

BRIDGE_VERSION = "1.0.0"


def build_health_snapshot(
    connection: ConnectionManager,
    last_tick_at: datetime | None = None,
    last_history_sync_at: datetime | None = None,
    terminal_build: int | None = None,
) -> HealthSnapshot:
    last_ping_monotonic = connection.last_ping_monotonic()
    last_ping_at = None
    if last_ping_monotonic is not None:
        # `time.monotonic()` has no wall-clock anchor; report "now" as a
        # best-effort wall-clock stamp for the UI rather than exposing
        # the meaningless monotonic float directly.
        last_ping_at = datetime.now(timezone.utc)

    return HealthSnapshot(
        connection_state=connection.state,
        latency_ms=connection.last_latency_ms(),
        connection_uptime_seconds=connection.uptime_seconds(),
        last_heartbeat_at=last_ping_at,
        last_tick_at=last_tick_at,
        last_history_sync_at=last_history_sync_at,
        last_ping_at=last_ping_at,
        terminal_build=terminal_build,
        bridge_version=BRIDGE_VERSION,
    )
