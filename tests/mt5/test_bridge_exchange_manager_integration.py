"""`BridgeExchangeManager` integration -- full export/validate/import
cycle, counters increment, audit events recorded, and a backward-
compatibility check that Phase 19.0's untouched per-kind
`bridge_manager.py`/`json_bridge.py` functions still work unchanged."""

import json
from pathlib import Path

import pytest

from app.mt5.audit import MT5AuditEventType
from app.mt5.bridge_exchange_manager import BridgeExchangeManager
from app.mt5.terminal_manager import MT5Manager
from tests.mt5.conftest import requires_real_terminal


@pytest.fixture
def bridge(mt5_manager: MT5Manager, tmp_path: Path) -> BridgeExchangeManager:
    return BridgeExchangeManager(state_dir=tmp_path / "mt5_state", manager=mt5_manager)


def test_export_increments_counter_and_audits(bridge: BridgeExchangeManager) -> None:
    document = bridge.export()
    health = bridge.get_health()
    assert health.export_count == 1
    assert health.last_export_at is not None
    kinds = [e.event_type for e in bridge.list_recent_audit_events()]
    assert MT5AuditEventType.BRIDGE_EXPORTED in kinds
    assert document["checksum"]


def test_validate_valid_document_records_ok(bridge: BridgeExchangeManager) -> None:
    document = bridge.export()
    issues = bridge.validate(document)
    assert issues == []
    health = bridge.get_health()
    assert health.last_validation_ok is True


def test_validate_invalid_document_audits_failure(bridge: BridgeExchangeManager) -> None:
    issues = bridge.validate({"not": "valid"})
    assert issues
    health = bridge.get_health()
    assert health.last_validation_ok is False
    kinds = [e.event_type for e in bridge.list_recent_audit_events()]
    assert MT5AuditEventType.BRIDGE_VALIDATION_FAILED in kinds


def test_import_request_health_kind_never_touches_export_validation_schema(bridge: BridgeExchangeManager) -> None:
    # Regression test for the bug caught during development: import
    # requests have their own {"kind","params"} shape and must NOT be
    # validated against the combined-document schema (which would
    # reject every legal import for "missing version/timestamp").
    result = bridge.import_request(json.dumps({"kind": "HEALTH_REQUEST", "params": {}}))
    assert result.success is True
    assert result.issues == []
    assert result.result["kind"] == "HEALTH_REQUEST"


def test_import_request_increments_counter_and_audits(bridge: BridgeExchangeManager) -> None:
    bridge.import_request(json.dumps({"kind": "REFRESH_REQUEST"}))
    health = bridge.get_health()
    assert health.import_count == 1
    kinds = [e.event_type for e in bridge.list_recent_audit_events()]
    assert MT5AuditEventType.BRIDGE_IMPORTED in kinds


def test_import_request_forbidden_keyword_does_not_increment_import_counter(bridge: BridgeExchangeManager) -> None:
    result = bridge.import_request(json.dumps({"kind": "SELECT_SYMBOL", "params": {"symbol": "EURUSD"}, "sell": True}))
    assert result.success is False
    health = bridge.get_health()
    assert health.import_count == 0


def test_payload_count_is_export_plus_import(bridge: BridgeExchangeManager) -> None:
    bridge.export()
    bridge.import_request(json.dumps({"kind": "REFRESH_REQUEST"}))
    health = bridge.get_health()
    assert health.payload_count == 2


def test_transport_status_always_not_implemented(bridge: BridgeExchangeManager) -> None:
    assert bridge.get_health().transport_status == "not implemented"
    for transport in bridge.list_transports():
        assert transport.display_name


def test_state_persists_across_instances(mt5_manager: MT5Manager, tmp_path: Path) -> None:
    state_dir = tmp_path / "mt5_state"
    first = BridgeExchangeManager(state_dir=state_dir, manager=mt5_manager)
    first.export()
    second = BridgeExchangeManager(state_dir=state_dir, manager=mt5_manager)
    assert second.get_health().export_count == 1


def test_schema_version_and_transports_delegate_to_existing_bridge_manager(bridge: BridgeExchangeManager) -> None:
    from app.mt5 import bridge_manager

    assert bridge.schema_version() == bridge_manager.schema_version()
    assert len(bridge.list_transports()) == len(bridge_manager.list_transports())
    assert bridge.preview_payload() == bridge_manager.preview_payload()


def test_phase_19_0_per_kind_functions_still_work_unchanged() -> None:
    """Backward compatibility: the exact free functions Phase 19.0 built
    (and `26_MT5_Integration.py`'s Bridge tab already calls) must still
    work exactly as before -- this phase only adds alongside them."""
    from app.mt5 import bridge_manager
    from app.mt5.json_bridge import sample_payload
    from app.mt5.mt5_models import AccountInfo

    assert bridge_manager.schema_version() == "1.0.0"
    transports = bridge_manager.list_transports()
    assert len(transports) == 2
    payload = bridge_manager.preview_payload()
    assert payload == sample_payload()

    from app.mt5.json_bridge import account_snapshot_json

    info = AccountInfo(login=1, server="s", currency="USD", balance=1.0, equity=1.0, margin=0.0, margin_free=1.0, leverage=1, trade_allowed=True)
    envelope = json.loads(account_snapshot_json(info))
    assert envelope["kind"] == "account_snapshot"


@requires_real_terminal
def test_real_full_cycle_export_validate_import(bridge: BridgeExchangeManager, mt5_manager: MT5Manager) -> None:
    from app.mt5.mt5_models import ConnectionState

    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        document = bridge.export()
        assert bridge.validate(document) == []

        result = bridge.import_request(json.dumps({"kind": "DIAGNOSTIC_REQUEST"}))
        assert result.success is True

        health = bridge.get_health()
        assert health.export_count == 1
        assert health.import_count == 1
    finally:
        mt5_manager.disconnect()
