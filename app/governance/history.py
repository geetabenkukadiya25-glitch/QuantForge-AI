"""Offline, JSON-only governance-record history (Phase 17.8) -- mirrors
`app.workflow.workflow_history.WorkflowHistoryStore` exactly: append-only
`.jsonl`, one full `GovernanceRecord` snapshot per status change, no
database, graceful degrade on a corrupt file.
"""

import json
from pathlib import Path

from app.governance.governance_models import GovernanceRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RECORDS = 2000


class GovernanceHistoryStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "governance_history.jsonl"

    def record(self, record: GovernanceRecord) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")
        self._trim_if_needed()

    def list_records(self, record_id: str | None = None, limit: int = 200) -> list[GovernanceRecord]:
        file = self._file()
        if not file.exists():
            return []
        records: list[GovernanceRecord] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                snapshot = GovernanceRecord.from_dict(json.loads(line))
                if record_id is None or snapshot.id == record_id:
                    records.append(snapshot)
        except (json.JSONDecodeError, OSError):
            logger.warning("Governance history log is unreadable.")
            return []
        records.sort(key=lambda r: r.updated_at, reverse=True)
        return records[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_RECORDS:
            file.write_text("\n".join(lines[-_MAX_RECORDS:]) + "\n", encoding="utf-8")
