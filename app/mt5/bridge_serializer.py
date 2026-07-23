"""Thin bridge-document-level wrappers (Phase 19.1), per the spec's
explicit list: `serialize`/`deserialize`/`checksum`/`pretty_json`/
`schema_version`. No `json.dumps`/`json.loads` logic beyond what these
five functions need -- mirrors the thin-wrapper shape already used by
`app.governance.serializer`/`app.cloud_sync.sync_serializer`.
"""

import json
from typing import Any

from app.core.checksums import compute_checksum
from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION


def serialize(document: dict[str, Any]) -> str:
    return json.dumps(document)


def deserialize(raw: str) -> dict[str, Any]:
    """Raises `json.JSONDecodeError` on malformed input -- callers that
    need graceful degradation should validate first via
    `bridge_validator.validate_json`, which never raises."""
    return json.loads(raw)


def checksum(document: dict[str, Any]) -> str:
    """Recomputes over every field except an existing `checksum` field
    (if present), so this is safe to call on a document that already
    carries one, e.g. to verify it."""
    payload = {k: v for k, v in document.items() if k != "checksum"}
    return compute_checksum(payload)


def pretty_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True)


def schema_version() -> str:
    """Same constant `app.mt5.bridge_manager.schema_version()` already
    reads -- one source of truth, two thin call sites (the same pattern
    already established between that function and `bridge_protocol.py`
    in Phase 19.0)."""
    return BRIDGE_SCHEMA_VERSION
