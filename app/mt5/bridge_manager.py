"""Orchestrates `json_bridge`/`bridge_protocol`/`ipc` for the UI's Bridge
tab (Phase 19.0). Tracks the bridge schema version and lists available
(placeholder) transports -- never sends anything anywhere.
"""

from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION
from app.mt5.ipc import BridgeTransport, LocalSocketTransport, NamedPipeTransport
from app.mt5.json_bridge import sample_payload

_TRANSPORTS: list[type[BridgeTransport]] = [NamedPipeTransport, LocalSocketTransport]


def schema_version() -> str:
    return BRIDGE_SCHEMA_VERSION


def list_transports() -> list[BridgeTransport]:
    return [cls() for cls in _TRANSPORTS]


def preview_payload() -> dict:
    return sample_payload()
