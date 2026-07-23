"""Offline, JSON-only sync-operation history (Phase 17.9) -- mirrors
`app.workflow.workflow_history.WorkflowHistoryStore` exactly: append-only
`.jsonl`, one full `SyncOperation` snapshot per status change, no
database, graceful degrade on a corrupt file.
"""

import json
from pathlib import Path

from app.cloud_sync.cloud_models import SyncOperation
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RECORDS = 2000


class SyncHistoryStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "cloud_sync_history.jsonl"

    def record(self, operation: SyncOperation) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(operation.to_dict()) + "\n")
        self._trim_if_needed()

    def list_records(self, operation_id: str | None = None, limit: int = 200) -> list[SyncOperation]:
        file = self._file()
        if not file.exists():
            return []
        records: list[SyncOperation] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                operation = SyncOperation.from_dict(json.loads(line))
                if operation_id is None or operation.id == operation_id:
                    records.append(operation)
        except (json.JSONDecodeError, OSError):
            logger.warning("Cloud Sync history log is unreadable.")
            return []
        # `created_at` is fixed at operation creation and never changes
        # across snapshots of the SAME operation -- sorting by it alone
        # can't distinguish an operation's own history entries from each
        # other. Prefer the most recently-set timestamp instead (mirrors
        # `WorkflowHistoryStore`'s `started_at or ended_at` fallback).
        records.sort(key=lambda r: r.completed_at or r.started_at or r.created_at, reverse=True)
        return records[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_RECORDS:
            file.write_text("\n".join(lines[-_MAX_RECORDS:]) + "\n", encoding="utf-8")
