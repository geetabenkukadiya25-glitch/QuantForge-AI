"""`bridge_export.py`/`bridge_serializer.py` -- round-trip: export ->
serialize -> deserialize -> validate -> zero issues; checksum
recomputation matches. Guarded by `requires_real_terminal` for the
real-data assertions; the disconnected-degrade path is tested
unconditionally."""

import json

import pytest

from app.mt5.bridge_export import export_document
from app.mt5.bridge_serializer import checksum, deserialize, pretty_json, schema_version, serialize
from app.mt5.bridge_validator import validate_document
from app.mt5.mt5_models import ConnectionState
from app.mt5.terminal_manager import MT5Manager
from tests.mt5.conftest import requires_real_terminal


def test_export_while_disconnected_degrades_honestly(mt5_manager) -> None:
    document = export_document(mt5_manager)
    assert document["version"]
    assert document["timestamp"]
    # dict-typed fields degrade to an explicit "unavailable" marker...
    assert document["terminal"] == {"available": False, "reason": "Cannot read terminal info -- not connected."}
    # ...list-typed fields degrade to an empty list, matching their
    # declared type so the document still passes schema validation.
    assert document["symbols"] == []
    assert document["positions"] == []
    assert document["orders"] == []
    assert "checksum" in document


def test_export_document_type_checks_pass_validation(mt5_manager) -> None:
    document = export_document(mt5_manager)
    # Even the disconnected-degrade shape (dicts with "available": False)
    # satisfies the validator's type checks -- no issues beyond content.
    issues = validate_document(document)
    assert issues == []


def test_serialize_deserialize_round_trip(mt5_manager) -> None:
    document = export_document(mt5_manager)
    raw = serialize(document)
    round_tripped = deserialize(raw)
    assert round_tripped == document


def test_checksum_function_matches_document_field(mt5_manager) -> None:
    document = export_document(mt5_manager)
    assert checksum(document) == document["checksum"]


def test_pretty_json_is_valid_json(mt5_manager) -> None:
    document = export_document(mt5_manager)
    pretty = pretty_json(document)
    assert json.loads(pretty) == document
    assert "\n" in pretty  # actually indented, not a one-liner


def test_schema_version_matches_bridge_protocol_constant() -> None:
    from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION

    assert schema_version() == BRIDGE_SCHEMA_VERSION


@requires_real_terminal
def test_real_export_full_round_trip(mt5_manager: MT5Manager) -> None:
    state = mt5_manager.connect()
    if state != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        document = export_document(mt5_manager)
        assert document["terminal"].get("connected") is True
        assert "login" in document["account"]
        assert isinstance(document["positions"], list)
        assert isinstance(document["orders"], list)

        raw = serialize(document)
        round_tripped = deserialize(raw)
        issues = validate_document(round_tripped)
        assert issues == []
        assert checksum(round_tripped) == round_tripped["checksum"]
    finally:
        mt5_manager.disconnect()


@requires_real_terminal
def test_real_export_with_history_and_ticks(mt5_manager: MT5Manager) -> None:
    state = mt5_manager.connect()
    if state != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        symbols = [s for s in mt5_manager.list_symbols() if s.visible]
        if not symbols:
            pytest.skip("No visible symbols on this terminal's Market Watch.")
        document = export_document(mt5_manager, history_symbol=symbols[0].name, tick_symbol=symbols[0].name, history_count=5, tick_count=5)
        assert "history" in document
        assert "ticks" in document
        assert validate_document(document) == []
    finally:
        mt5_manager.disconnect()
