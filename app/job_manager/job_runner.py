"""The single background dispatcher (Phase 18.4).

One lazily-started daemon thread per `JobManager`, processing one job at
a time -- `max_concurrent = 1` by design: engines remain fully
synchronous, and a single dispatcher loop keeps QUEUED-vs-RUNNING
visibility simple and race-free without a thread pool. This module never
imports any engine; it only ever calls the opaque `job.operation(...)`
callable a page supplied.
"""

import threading
from datetime import datetime, timezone
from typing import Callable

from app.job_manager.exceptions import JobCancelledError
from app.job_manager.job import Job
from app.job_manager.job_events import JobEventLog
from app.job_manager.job_history import JobHistoryStore
from app.job_manager.job_queue import JobQueue
from app.job_manager.job_state import JobState
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobDispatcher:
    def __init__(
        self,
        queue: JobQueue,
        history: JobHistoryStore,
        events: JobEventLog,
        get_job: Callable[[str], Job | None],
    ) -> None:
        self._queue = queue
        self._history = history
        self._events = events
        self._get_job = get_job
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()
        self._stop_requested = False

    def ensure_started(self) -> None:
        with self._start_lock:
            if self._thread is None or not self._thread.is_alive():
                self._stop_requested = False
                self._thread = threading.Thread(target=self._run_loop, name="job-dispatcher", daemon=True)
                self._thread.start()

    def stop(self) -> None:
        self._stop_requested = True

    def _run_loop(self) -> None:
        while not self._stop_requested:
            job_id = self._queue.pop_blocking(timeout=0.5)
            if job_id is None:
                continue
            job = self._get_job(job_id)
            if job is None:
                continue
            self._run_job(job)

    def _run_job(self, job: Job) -> None:
        if job.cancel_requested:
            job.state = JobState.CANCELLED
            job.ended_at = datetime.now(timezone.utc)
            self._finish(job, "cancelled", f"Job '{job.name}' was cancelled before it started.")
            return

        job.state = JobState.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self._events.append(job.id, "started", f"Job '{job.name}' started.")

        try:
            job.result = job.operation(job)
        except JobCancelledError:
            job.state = JobState.CANCELLED
            job.ended_at = datetime.now(timezone.utc)
            self._finish(job, "cancelled", f"Job '{job.name}' was cancelled.")
        except Exception as exc:  # noqa: BLE001 -- surfaced on the job, never swallowed
            job.state = JobState.FAILED
            job.error = str(exc)
            job.ended_at = datetime.now(timezone.utc)
            logger.warning(f"Job '{job.id}' ({job.name}) failed: {exc}")
            self._finish(job, "failed", f"Job '{job.name}' failed: {exc}")
        else:
            job.state = JobState.COMPLETED
            job.ended_at = datetime.now(timezone.utc)
            self._finish(job, "completed", f"Job '{job.name}' completed.")

    def _finish(self, job: Job, kind: str, message: str) -> None:
        self._history.record(job.to_record())
        self._events.append(job.id, kind, message)
