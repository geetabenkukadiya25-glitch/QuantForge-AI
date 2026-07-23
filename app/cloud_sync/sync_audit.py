"""Offline, timestamp-only audit trail for Cloud Sync (Phase 17.9).
Mirrors `app.governance.audit.GovernanceAuditLogStore` exactly -- one
JSON line per event, no user identity, no network call, no database.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class SyncAuditEventType(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRIED = "RETRIED"
    PROVIDER_REGISTERED = "PROVIDER_REGISTERED"
    ARTIFACT_REGISTERED = "ARTIFACT_REGISTERED"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    POLICY_UPDATED = "POLICY_UPDATED"


@dataclass(frozen=True)
class SyncAuditEvent:
    event_type: SyncAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "SyncAuditEvent":
        return SyncAuditEvent(
            event_type=SyncAuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class SyncAuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "cloud_sync_audit_log.jsonl"

    def record(self, event_type: SyncAuditEventType, key: str) -> None:
        event = SyncAuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[SyncAuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[SyncAuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = SyncAuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Cloud Sync audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
