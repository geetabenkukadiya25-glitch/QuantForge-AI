"""Offline, timestamp-only audit trail for Dataset Manager (Phase 18.6).

Appends one JSON line per event to a local file -- no user identity, no
network call, no database. Mirrors
`app.strategy_library.audit_log.AuditLogStore` exactly.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dataset_manager.models import DatasetAuditEvent, DatasetAuditEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_EVENTS = 2000


class DatasetAuditLogStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "dataset_audit_log.jsonl"

    def record(self, event_type: DatasetAuditEventType, key: str) -> None:
        event = DatasetAuditEvent(event_type=event_type, key=key, timestamp=datetime.now(timezone.utc))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")
        self._trim_if_needed()

    def list_events(self, key: str | None = None, limit: int = 200) -> list[DatasetAuditEvent]:
        file = self._file()
        if not file.exists():
            return []
        events: list[DatasetAuditEvent] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = DatasetAuditEvent.from_dict(json.loads(line))
                if key is None or event.key == key:
                    events.append(event)
        except (json.JSONDecodeError, OSError):
            logger.warning("Dataset audit log is unreadable.")
            return []
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_EVENTS:
            file.write_text("\n".join(lines[-_MAX_EVENTS:]) + "\n", encoding="utf-8")
