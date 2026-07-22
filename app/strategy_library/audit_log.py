"""Offline, timestamp-only audit trail (Phase 18 rule 29).

Appends one JSON line per event to a local file -- no user identity, no
network call, no database. Every mutating/interactive manager operation
(create, open, edit, save, compile, validate, export, import, delete)
records exactly one event here.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.strategy_library.models import AuditEvent, AuditEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class AuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "audit_log.jsonl"

    def record(self, event_type: AuditEventType, key: str) -> None:
        event = AuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[AuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[AuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = AuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
