"""`bridge_protocol.py`/`json_bridge.py`/`bridge_manager.py` -- schema
round-trip, no `app.ea_generator` import anywhere in this package."""

import json

import pytest

from app.mt5 import bridge_manager
from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION, envelope
from app.mt5.json_bridge import health_snapshot_json, sample_payload
from app.mt5.mt5_models import ConnectionState, HealthSnapshot


def test_envelope_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        envelope("not_a_real_kind", {})


def test_envelope_shape() -> None:
    doc = envelope("terminal_snapshot", {"a": 1})
    assert doc["schema_version"] == BRIDGE_SCHEMA_VERSION
    assert doc["kind"] == "terminal_snapshot"
    assert doc["payload"] == {"a": 1}


def test_health_snapshot_json_round_trips_through_json_module() -> None:
    snapshot = HealthSnapshot(
        connection_state=ConnectionState.CONNECTED,
        latency_ms=1.0,
        connection_uptime_seconds=1.0,
        last_heartbeat_at=None,
        last_tick_at=None,
        last_history_sync_at=None,
        last_ping_at=None,
        terminal_build=6033,
        bridge_version="1.0.0",
    )
    parsed = json.loads(health_snapshot_json(snapshot))
    assert parsed["kind"] == "health_snapshot"
    assert parsed["payload"]["connection_state"] == "CONNECTED"


def test_sample_payload_is_schema_shaped() -> None:
    payload = sample_payload()
    assert payload["schema_version"] == BRIDGE_SCHEMA_VERSION
    assert "kind" in payload and "payload" in payload


def test_bridge_manager_lists_transports_and_version() -> None:
    assert bridge_manager.schema_version() == BRIDGE_SCHEMA_VERSION
    transports = bridge_manager.list_transports()
    assert len(transports) == 2
    for transport in transports:
        assert transport.display_name


def test_no_ea_generator_import_in_bridge_protocol() -> None:
    import inspect

    import app.mt5.bridge_protocol as module

    source = inspect.getsource(module)
    assert "import app.ea_generator" not in source
    assert "from app.ea_generator" not in source
