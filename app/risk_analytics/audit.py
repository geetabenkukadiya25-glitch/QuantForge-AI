"""Offline, timestamp-only audit trail for Risk Analytics (Phase 17.7).
Byte-for-byte mirror of `app.workflow.audit_log.WorkflowAuditLogStore`'s
pattern -- one JSON line per event, no user identity, no network call,
no database.
"""

import json
from pathlib import Path

from app.risk_analytics.risk_models import RiskAuditEvent, RiskAuditEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class RiskAuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "risk_audit_log.jsonl"

    def record(self, event_type: RiskAuditEventType, key: str) -> None:
        from datetime import datetime, timezone

        event = RiskAuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[RiskAuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[RiskAuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = RiskAuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Risk audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
