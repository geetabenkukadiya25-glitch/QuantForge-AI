"""In-process job lifecycle event log (Phase 18.4).

Appended to only by the dispatcher thread; drained only by the main
Streamlit script thread, which turns new events into calls to the
existing `app.ui.components.notifications.notify(...)` -- this module
itself never calls any `st.*` API, so it's safe to append from a
background thread.
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

JobEventKind = Literal["started", "completed", "cancelled", "failed"]


@dataclass(frozen=True)
class JobEvent:
    id: int
    job_id: str
    kind: JobEventKind
    message: str
    timestamp: datetime


class JobEventLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[JobEvent] = []
        self._next_id = 1

    def append(self, job_id: str, kind: JobEventKind, message: str) -> JobEvent:
        with self._lock:
            event = JobEvent(id=self._next_id, job_id=job_id, kind=kind, message=message, timestamp=datetime.now(timezone.utc))
            self._next_id += 1
            self._events.append(event)
            return event

    def events_since(self, last_id: int) -> list[JobEvent]:
        with self._lock:
            return [e for e in self._events if e.id > last_id]

    @property
    def latest_id(self) -> int:
        with self._lock:
            return self._events[-1].id if self._events else 0
