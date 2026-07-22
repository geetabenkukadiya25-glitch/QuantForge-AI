"""The central `JobManager` (Phase 18.4) -- what every dashboard submits
its heavy operation to, instead of calling an engine directly. Zero
engine imports: `operation` is an opaque callable the caller provides.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Callable

from app.job_manager.exceptions import JobNotFoundError
from app.job_manager.job import Job
from app.job_manager.job_events import JobEvent, JobEventLog
from app.job_manager.job_history import JobHistoryStore
from app.job_manager.job_progress import JobProgress
from app.job_manager.job_queue import JobQueue
from app.job_manager.job_runner import JobDispatcher
from app.job_manager.job_state import JobState, is_terminal
from app.job_manager.models import JobCategory


class JobManager:
    def __init__(self, history_dir) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._queue = JobQueue()
        self._history = JobHistoryStore(history_dir)
        self._events = JobEventLog()
        self._dispatcher = JobDispatcher(self._queue, self._history, self._events, self.get)

    # ------------------------------------------------------------------
    # Submission / lifecycle
    # ------------------------------------------------------------------

    def submit(
        self,
        name: str,
        category: JobCategory,
        operation: Callable[[Job], Any],
        owner_page: str,
        step_names: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """`operation` receives the `Job` itself (so it can call
        `job.progress.step(i)` for coarse step boundaries and
        `job.progress.make_progress_callback(job)` to hand engines that
        support one a fine-grained `progress_callback`) and returns the
        job's `result`. It is never inspected or modified by the Job
        Manager -- it's the exact same engine call a page already made,
        just invoked from the dispatcher thread instead of inline."""
        job = Job(
            name=name,
            category=category,
            owner_page=owner_page,
            operation=operation,
            progress=JobProgress(step_names),
            metadata=metadata or {},
        )
        with self._lock:
            self._jobs[job.id] = job
        self._queue.push(job.id)
        self._dispatcher.ensure_started()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, state: JobState | None = None, category: JobCategory | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        if state is not None:
            jobs = [j for j in jobs if j.state == state]
        if category is not None:
            jobs = [j for j in jobs if j.category == category]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job is None:
            raise JobNotFoundError(f"No job with id '{job_id}'.")
        if is_terminal(job.state):
            return job
        job.cancel_requested = True
        if job.state == JobState.QUEUED and self._queue.remove(job_id):
            job.state = JobState.CANCELLED
            job.ended_at = datetime.now(timezone.utc)
            self._history.record(job.to_record())
            self._events.append(job.id, "cancelled", f"Job '{job.name}' was cancelled.")
        # If RUNNING, `cancel_requested` is picked up cooperatively the
        # next time the operation reports progress (see job_progress.py);
        # an operation with no progress callback cannot be interrupted
        # until it returns on its own -- that limitation is never hidden.
        return job

    def cancel_running(self) -> Job | None:
        running = self.list(state=JobState.RUNNING)
        if not running:
            return None
        return self.cancel(running[0].id)

    def retry(self, job_id: str) -> Job:
        """Re-submit an equivalent job with the same operation/metadata.
        Only works for jobs still resident in this process's in-memory
        registry (the `operation` closure is never persisted to history,
        since callables aren't JSON-serializable) -- an honest limitation
        of the "JSON only, no database" persistence model."""
        job = self.get(job_id)
        if job is None:
            raise JobNotFoundError(f"No job with id '{job_id}'.")
        return self.submit(
            name=job.name,
            category=job.category,
            operation=job.operation,
            owner_page=job.owner_page,
            step_names=[s.name for s in job.progress.tracker.steps],
            metadata=dict(job.metadata),
        )

    def clear_finished(self) -> int:
        """Remove terminal jobs from the in-memory registry (does not
        touch persisted history)."""
        with self._lock:
            finished_ids = [jid for jid, j in self._jobs.items() if is_terminal(j.state)]
            for jid in finished_ids:
                del self._jobs[jid]
            return len(finished_ids)

    # ------------------------------------------------------------------
    # Status / events / history
    # ------------------------------------------------------------------

    def status_counts(self) -> dict[str, int]:
        jobs = self.list()
        today = datetime.now(timezone.utc).date()
        completed_today = sum(
            1 for j in jobs if j.state == JobState.COMPLETED and j.ended_at is not None and j.ended_at.date() == today
        )
        return {
            "running_jobs": sum(1 for j in jobs if j.state == JobState.RUNNING),
            "queued_jobs": sum(1 for j in jobs if j.state == JobState.QUEUED),
            "completed_jobs_today": completed_today,
        }

    def events_since(self, last_id: int) -> list[JobEvent]:
        return self._events.events_since(last_id)

    def latest_event_id(self) -> int:
        return self._events.latest_id

    def history(self, limit: int = 200):
        return self._history.list_records(limit=limit)
