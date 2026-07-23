"""Serializes current read-only MT5 snapshots into `bridge_protocol`-
shaped JSON documents (Phase 19.0). Produces real JSON from real,
already-fetched data -- it does not perform any I/O of its own and does
not transmit anything (see `ipc.py` for why transport is unbuilt).
"""

import json
from typing import Any

from app.mt5.bridge_protocol import envelope
from app.mt5.mt5_models import AccountInfo, Bar, HealthSnapshot, SymbolInfo, TerminalInfo


def terminal_snapshot_json(info: TerminalInfo) -> str:
    return json.dumps(envelope("terminal_snapshot", info.to_dict()))


def account_snapshot_json(info: AccountInfo) -> str:
    return json.dumps(envelope("account_snapshot", info.to_dict()))


def symbol_snapshot_json(info: SymbolInfo) -> str:
    return json.dumps(envelope("symbol_snapshot", info.to_dict()))


def bar_snapshot_json(bars: list[Bar]) -> str:
    return json.dumps(envelope("bar_snapshot", {"bars": [b.to_dict() for b in bars]}))


def health_snapshot_json(snapshot: HealthSnapshot) -> str:
    return json.dumps(envelope("health_snapshot", snapshot.to_dict()))


def sample_payload() -> dict[str, Any]:
    """A schema-shaped example payload for the UI's Bridge tab preview --
    illustrative only, not sourced from a real connection."""
    return envelope(
        "health_snapshot",
        {
            "connection_state": "DISCONNECTED",
            "latency_ms": None,
            "bridge_version": "1.0.0",
            "note": "Example shape only -- connect to see real data.",
        },
    )
