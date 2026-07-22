"""Bridges a `Job` to the existing, unmodified `ProgressTracker`
(`app.ui.progress`) -- the ONLY progress system in the project. This
module never renders anything on its own initiative and never invents a
second progress mechanism; it only owns one `ProgressTracker` instance
per job and forwards calls to it, thread-safely.
"""

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Iterator

from app.job_manager.exceptions import JobCancelledError
from app.ui.progress import ProgressTracker

if TYPE_CHECKING:
    from app.job_manager.job import Job


class JobProgress:
    """Owns one `ProgressTracker` for a single job plus the lock that
    guards it, since the dispatcher thread (writer) and the Streamlit
    script thread (reader, via `render()`) both touch it."""

    def __init__(self, step_names: list[str]) -> None:
        self._lock = threading.Lock()
        self.tracker = ProgressTracker(step_names)

    def start_step(self, index: int) -> None:
        with self._lock:
            self.tracker.start_step(index)

    def complete_step(self, index: int | None = None) -> None:
        with self._lock:
            self.tracker.complete_step(index)

    @contextmanager
    def step(self, index: int) -> Iterator[None]:
        """Bracket one already-existing stage of an operation with
        `start_step`/`complete_step` -- the same shape as
        `app.ui.progress.tracked_step`, just against this job's own
        tracker instead of a page-local one. Operations that build a
        few objects then hand off to an engine's own `progress_callback`
        for the fine-grained middle step use this for the surrounding
        (usually instantaneous) steps, exactly like every page already
        did with `tracked_step` before Phase 18.4."""
        self.start_step(index)
        try:
            yield
        finally:
            self.complete_step(index)

    @property
    def percentage(self) -> int:
        with self._lock:
            return self.tracker.percentage

    def estimated_remaining_seconds(self) -> float | None:
        with self._lock:
            return self.tracker.estimated_remaining_seconds()

    def render(self, container=None) -> None:
        """Presentation-only; call only from the main Streamlit script
        thread (never from the dispatcher thread)."""
        with self._lock:
            self.tracker.render(container)

    def make_progress_callback(self, job: "Job") -> Callable[[int, int, str], None]:
        """Build a `(current, total, operation) -> None` callback in the
        exact shape `app.ui.progress.make_item_progress_callback` already
        expects engines to accept (e.g.
        `BacktestingEngine.try_execute(..., progress_callback=...)`).
        Raises `JobCancelledError` if the owning job has been
        cancel-requested, so a cooperative engine unwinds the next time
        it reports progress -- this is the only way a RUNNING job can be
        interrupted, since engines are never modified to support real
        cancellation."""

        def _callback(current: int, total: int, operation: str) -> None:
            if job.cancel_requested:
                raise JobCancelledError(f"Job '{job.id}' was cancelled.")
            with self._lock:
                self.tracker.update_item_progress(current, total, operation)

        return _callback
