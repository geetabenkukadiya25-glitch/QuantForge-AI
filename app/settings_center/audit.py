"""Offline, timestamp-only audit trail for the Settings Center (Phase
18.8). Mirrors `app.governance.audit.GovernanceAuditLogStore` exactly --
one JSON line per event, no user identity, no network call, no database.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class SettingsAuditEventType(str, Enum):
    CREATED = "CREATED"
    SECTION_UPDATED = "SECTION_UPDATED"
    EXPORTED = "EXPORTED"
    IMPORTED = "IMPORTED"
    BACKED_UP = "BACKED_UP"
    RESTORED = "RESTORED"
    RESET_TO_DEFAULTS = "RESET_TO_DEFAULTS"
    PATH_CHANGED = "PATH_CHANGED"
    PATH_RESET = "PATH_RESET"


@dataclass(frozen=True)
class SettingsAuditEvent:
    event_type: SettingsAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "SettingsAuditEvent":
        return SettingsAuditEvent(
            event_type=SettingsAuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class SettingsAuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "settings_audit_log.jsonl"

    def record(self, event_type: SettingsAuditEventType, key: str) -> None:
        event = SettingsAuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[SettingsAuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[SettingsAuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = SettingsAuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Settings audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
