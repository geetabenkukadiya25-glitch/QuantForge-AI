"""Offline, timestamp-only audit trail for Governance (Phase 17.8).
Mirrors `app.workflow.audit_log.WorkflowAuditLogStore` exactly -- one
JSON line per event, no user identity beyond the reviewer name already
carried on the event, no network call, no database.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class GovernanceAuditEventType(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REOPENED = "REOPENED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMMENTED = "COMMENTED"
    DELETED = "DELETED"
    COMPLIANCE_CHECKED = "COMPLIANCE_CHECKED"


@dataclass(frozen=True)
class GovernanceAuditEvent:
    event_type: GovernanceAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "GovernanceAuditEvent":
        return GovernanceAuditEvent(
            event_type=GovernanceAuditEventType(data["event_type"]),
            key=data["key"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class GovernanceAuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "governance_audit_log.jsonl"

    def record(self, event_type: GovernanceAuditEventType, key: str) -> None:
        event = GovernanceAuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[GovernanceAuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[GovernanceAuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = GovernanceAuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Governance audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
