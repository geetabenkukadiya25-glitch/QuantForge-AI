"""Offline, timestamp-only audit trail for the MT5 Integration Layer
(Phase 19.0). Verbatim mirror of
`app.governance.audit.GovernanceAuditLogStore` -- one JSON line per
event, no network call, no database.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class MT5AuditEventType(str, Enum):
    CONNECT_ATTEMPTED = "CONNECT_ATTEMPTED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTION_LOST = "CONNECTION_LOST"
    RECONNECT_ATTEMPTED = "RECONNECT_ATTEMPTED"
    PING = "PING"
    DIAGNOSTICS_RUN = "DIAGNOSTICS_RUN"
    HISTORY_SYNCED = "HISTORY_SYNCED"
    TICKS_SYNCED = "TICKS_SYNCED"
    SETTINGS_UPDATED = "SETTINGS_UPDATED"
    ERROR = "ERROR"
    # Phase 19.1, additive -- JSON Bridge exchange events.
    BRIDGE_EXPORTED = "BRIDGE_EXPORTED"
    BRIDGE_IMPORTED = "BRIDGE_IMPORTED"
    BRIDGE_VALIDATION_FAILED = "BRIDGE_VALIDATION_FAILED"
    BRIDGE_SCHEMA_MISMATCH = "BRIDGE_SCHEMA_MISMATCH"


@dataclass(frozen=True)
class MT5AuditEvent:
    event_type: MT5AuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "MT5AuditEvent":
        return MT5AuditEvent(
            event_type=MT5AuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class MT5AuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "mt5_audit_log.jsonl"

    def record(self, event_type: MT5AuditEventType, key: str) -> None:
        event = MT5AuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[MT5AuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[MT5AuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = MT5AuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("MT5 audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
