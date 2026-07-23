"""Offline, JSON-only workflow run history (Phase 17.6) -- mirrors
`app.job_manager.job_history.JobHistoryStore` exactly: append-only
`.jsonl`, no database, graceful degrade on a corrupt file."""

import json
from pathlib import Path

from app.utils.logger import get_logger
from app.workflow.workflow_models import WorkflowRun

logger = get_logger(__name__)

_MAX_RECORDS = 2000


class WorkflowHistoryStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "workflow_history.jsonl"

    def record(self, run: WorkflowRun) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._file().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run.to_dict()) + "\n")
        self._trim_if_needed()

    def list_records(self, workflow_id: str | None = None, limit: int = 200) -> list[WorkflowRun]:
        file = self._file()
        if not file.exists():
            return []
        records: list[WorkflowRun] = []
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                run = WorkflowRun.from_dict(json.loads(line))
                if workflow_id is None or run.workflow_id == workflow_id:
                    records.append(run)
        except (json.JSONDecodeError, OSError):
            logger.warning("Workflow history log is unreadable.")
            return []
        records.sort(key=lambda r: (r.started_at or r.ended_at).isoformat() if (r.started_at or r.ended_at) else "", reverse=True)
        return records[:limit]

    def _trim_if_needed(self) -> None:
        file = self._file()
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) > _MAX_RECORDS:
            file.write_text("\n".join(lines[-_MAX_RECORDS:]) + "\n", encoding="utf-8")
