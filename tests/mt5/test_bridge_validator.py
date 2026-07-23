"""`bridge_validator.py` -- one test per failure mode, plus a fully
valid document passing with zero issues."""

import json

from app.core.checksums import compute_checksum
from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION
from app.mt5.bridge_validator import MAX_PAYLOAD_BYTES, BridgeValidator, validate_document, validate_json


def _minimal_valid_document() -> dict:
    doc = {
        "version": BRIDGE_SCHEMA_VERSION,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "terminal": {"connected": True},
        "account": {"login": 1},
        "symbols": [],
        "health": {"connection_state": "CONNECTED"},
    }
    doc["checksum"] = compute_checksum(doc)
    return doc


def test_fully_valid_document_has_zero_issues() -> None:
    assert validate_document(_minimal_valid_document()) == []


def test_missing_required_fields() -> None:
    issues = validate_document({})
    assert any("version" in i for i in issues)
    assert any("timestamp" in i for i in issues)


def test_unknown_field_flagged() -> None:
    doc = _minimal_valid_document()
    doc["not_a_real_field"] = 123
    issues = validate_document(doc)
    assert any("Unknown field 'not_a_real_field'" in i for i in issues)


def test_invalid_field_type() -> None:
    doc = _minimal_valid_document()
    doc["symbols"] = "not a list"
    issues = validate_document(doc)
    assert any("symbols" in i and "type" in i for i in issues)


def test_bad_timestamp() -> None:
    doc = _minimal_valid_document()
    doc["timestamp"] = "not-a-timestamp"
    del doc["checksum"]
    issues = validate_document(doc)
    assert any("timestamp" in i.lower() for i in issues)


def test_unsupported_schema_version_major_mismatch() -> None:
    doc = _minimal_valid_document()
    doc["version"] = "2.0.0"
    del doc["checksum"]
    issues = validate_document(doc)
    assert any("Unsupported schema version" in i for i in issues)


def test_checksum_mismatch() -> None:
    doc = _minimal_valid_document()
    doc["checksum"] = "0" * 64  # deliberately wrong
    issues = validate_document(doc)
    assert any("Checksum mismatch" in i for i in issues)


def test_malformed_json_never_raises() -> None:
    issues = validate_json("{not valid json")
    assert len(issues) == 1
    assert "Malformed JSON" in issues[0]


def test_top_level_not_an_object() -> None:
    issues = validate_json(json.dumps([1, 2, 3]))
    assert any("JSON object" in i for i in issues)


def test_oversized_payload_flagged() -> None:
    huge_doc = _minimal_valid_document()
    huge_doc["symbols"] = [{"padding": "x" * 1000} for _ in range(MAX_PAYLOAD_BYTES // 500)]
    raw = json.dumps(huge_doc)
    issues = validate_json(raw)
    assert any("exceeds" in i for i in issues)


def test_valid_json_round_trip_through_validate_json() -> None:
    doc = _minimal_valid_document()
    assert validate_json(json.dumps(doc)) == []


def test_bridge_validator_class_delegates_to_functions() -> None:
    validator = BridgeValidator()
    assert validator.validate_document(_minimal_valid_document()) == []
    assert validator.validate_json("{bad") != []
