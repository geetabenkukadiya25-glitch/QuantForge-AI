"""Thread-safe FIFO of queued workflow run ids (Phase 17.6) -- mirrors
`app.job_manager.job_queue.JobQueue` exactly."""

import threading
from collections import deque


class WorkflowQueue:
    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def push(self, run_id: str) -> None:
        with self._not_empty:
            self._items.append(run_id)
            self._not_empty.notify()

    def pop_blocking(self, timeout: float | None = None) -> str | None:
        with self._not_empty:
            if not self._items:
                self._not_empty.wait(timeout=timeout)
            if not self._items:
                return None
            return self._items.popleft()

    def remove(self, run_id: str) -> bool:
        with self._lock:
            try:
                self._items.remove(run_id)
            except ValueError:
                return False
            return True

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
