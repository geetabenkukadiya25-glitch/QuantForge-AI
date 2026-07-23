"""`BridgeValidator` (Phase 19.1) -- validates a JSON Bridge document.
Mirrors `app.cloud_sync.sync_validator`'s shape (`validate_x(...) ->
list[str]`, pure predicates, empty list = valid) -- genuinely new
content (no existing generic-JSON-document validator exists anywhere in
the repo), but not a new shape. Never raises for a bad document or
malformed JSON -- always returns explicit issues, so "never silently
ignore failures" holds by construction; the caller decides whether any
issue is fatal.
"""

import json
from datetime import datetime
from typing import Any

from app.core.checksums import compute_checksum
from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION

MAX_PAYLOAD_BYTES = 5_000_000

REQUIRED_FIELDS = frozenset({"version", "timestamp"})

# Every field the combined bridge document may legally carry, and the
# type each one must have when present. Anything outside this set is
# flagged as an "unknown field" issue.
KNOWN_FIELDS: dict[str, type] = {
    "version": str,
    "timestamp": str,
    "terminal": dict,
    "account": dict,
    "symbols": list,
    "positions": list,
    "orders": list,
    "history": list,
    "ticks": list,
    "health": dict,
    "diagnostics": dict,
    "compatibility": dict,
    "checksum": str,
}


def validate_json(raw: str) -> list[str]:
    """Malformed-JSON-safe: parses `raw` and validates the resulting
    document. Never raises -- a `json.JSONDecodeError` becomes one
    explicit issue instead of an exception escaping to the caller."""
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"Malformed JSON: {exc}"]
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        issues = [f"Payload size {len(raw.encode('utf-8'))} bytes exceeds the {MAX_PAYLOAD_BYTES}-byte limit."]
    else:
        issues = []
    if not isinstance(document, dict):
        return issues + ["Top-level payload must be a JSON object."]
    return issues + validate_document(document)


def validate_document(document: dict[str, Any]) -> list[str]:
    """Validates an already-parsed document dict. Does not re-check
    payload size (that requires the original JSON text -- see
    `validate_json`, which is the entry point that has it)."""
    issues: list[str] = []

    for field_name in REQUIRED_FIELDS:
        if field_name not in document:
            issues.append(f"Missing required field '{field_name}'.")

    for field_name in document:
        if field_name not in KNOWN_FIELDS:
            issues.append(f"Unknown field '{field_name}'.")

    for field_name, expected_type in KNOWN_FIELDS.items():
        if field_name in document and document[field_name] is not None and not isinstance(document[field_name], expected_type):
            issues.append(f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(document[field_name]).__name__}.")

    version = document.get("version")
    if isinstance(version, str):
        if version != BRIDGE_SCHEMA_VERSION:
            expected_major = BRIDGE_SCHEMA_VERSION.split(".")[0]
            actual_major = version.split(".")[0] if version else ""
            if actual_major != expected_major:
                issues.append(f"Unsupported schema version '{version}' -- this build produces/expects major version {expected_major}.")

    timestamp = document.get("timestamp")
    if isinstance(timestamp, str):
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            issues.append(f"Field 'timestamp' is not a valid ISO-8601 timestamp: '{timestamp}'.")

    checksum = document.get("checksum")
    if isinstance(checksum, str) and checksum:
        payload_without_checksum = {k: v for k, v in document.items() if k != "checksum"}
        recomputed = compute_checksum(payload_without_checksum)
        if recomputed != checksum:
            issues.append("Checksum mismatch -- the document's content does not match its declared 'checksum' field.")

    return issues


class BridgeValidator:
    """Thin, stateless wrapper class around the module-level functions
    above -- provided because the phase spec asks for a `BridgeValidator`
    type; the actual validation logic lives in the pure functions so it
    stays trivially unit-testable without instantiating anything."""

    def validate_json(self, raw: str) -> list[str]:
        return validate_json(raw)

    def validate_document(self, document: dict[str, Any]) -> list[str]:
        return validate_document(document)
