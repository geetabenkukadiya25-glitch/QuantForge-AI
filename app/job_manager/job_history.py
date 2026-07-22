"""Offline, JSON-only job history (Phase 18.4) -- mirrors
`app.strategy_library.audit_log.AuditLogStore` exactly: an append-only
`.jsonl` file, no database, no OS file lock, graceful degrade on a
corrupt file.
"""

import json
from pathlib import Path

from app.job_manager.models import JobRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RECORDS = 2000


class JobHistoryStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "jobs_history.jsonl"

    def record(self, record: JobRecord) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")
        self._trim_if_needed()

    def list_records(self, limit: int = 200) -> list[JobRecord]:
        file = self._file()
        if not file.exists():
            return []
        records: list[JobRecord] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                records.append(JobRecord.from_dict(json.loads(line)))
        except (json.JSONDecodeError, OSError):
            logger.warning("Job history log is unreadable.")
            return []
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_RECORDS:
            file.write_text("\n".join(lines[-_MAX_RECORDS:]) + "\n", encoding="utf-8")
