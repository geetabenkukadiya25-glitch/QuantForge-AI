"""Thread-safe FIFO of queued job ids (Phase 18.4)."""

import threading
from collections import deque


class JobQueue:
    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def push(self, job_id: str) -> None:
        with self._not_empty:
            self._items.append(job_id)
            self._not_empty.notify()

    def pop_blocking(self, timeout: float | None = None) -> str | None:
        """Block until a job id is available (or `timeout` elapses),
        returning `None` on timeout so the dispatcher loop can check its
        stop condition periodically."""
        with self._not_empty:
            if not self._items:
                self._not_empty.wait(timeout=timeout)
            if not self._items:
                return None
            return self._items.popleft()

    def remove(self, job_id: str) -> bool:
        """Remove a still-queued job (used by `cancel()`). Returns True
        if it was present and removed."""
        with self._lock:
            try:
                self._items.remove(job_id)
            except ValueError:
                return False
            return True

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
