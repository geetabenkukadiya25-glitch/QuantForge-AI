"""In-process workflow/step lifecycle event log (Phase 17.6) -- mirrors
`app.job_manager.job_events.JobEventLog`. Appended to only by the
workflow runner thread; drained only by the main Streamlit script thread
for the live Execution Timeline. Never calls any `st.*` API itself."""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

WorkflowEventKind = Literal[
    "run_queued", "run_started", "run_paused", "run_resumed", "run_cancelled", "run_completed", "run_failed",
    "step_started", "step_completed", "step_failed", "step_skipped", "step_retrying", "step_timed_out",
]


@dataclass(frozen=True)
class WorkflowEvent:
    id: int
    run_id: str
    kind: WorkflowEventKind
    message: str
    timestamp: datetime
    step_id: str | None = None


class WorkflowEventLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[WorkflowEvent] = []
        self._next_id = 1

    def append(self, run_id: str, kind: WorkflowEventKind, message: str, step_id: str | None = None) -> WorkflowEvent:
        with self._lock:
            event = WorkflowEvent(id=self._next_id, run_id=run_id, kind=kind, message=message, timestamp=datetime.now(timezone.utc), step_id=step_id)
            self._next_id += 1
            self._events.append(event)
            return event

    def events_since(self, last_id: int, run_id: str | None = None) -> list[WorkflowEvent]:
        with self._lock:
            events = [e for e in self._events if e.id > last_id]
            if run_id is not None:
                events = [e for e in events if e.run_id == run_id]
            return events

    @property
    def latest_id(self) -> int:
        with self._lock:
            return self._events[-1].id if self._events else 0
