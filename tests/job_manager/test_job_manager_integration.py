"""End-to-end tests against `JobManager` -- submit/complete, fail, cancel
(queued and cooperative-running), retry, clear, and status counts. Uses
fake `operation` callables only; never imports any engine, matching the
Job Manager's own zero-engine-import guarantee."""

import time

import pytest

from app.job_manager.job_manager import JobManager
from app.job_manager.job_state import JobState
from app.job_manager.models import JobCategory


def _wait_for(job, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while job.state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.01)


def _wait_for_history(job_manager: JobManager, job_id: str, timeout: float = 5.0):
    """History is written by the dispatcher thread right after (not
    atomically with) the state transition -- poll briefly rather than
    assuming the two are visible to another thread in the same instant."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        records = job_manager.history()
        match = next((r for r in records if r.id == job_id), None)
        if match is not None:
            return match
        time.sleep(0.01)
    return None


def test_submit_runs_and_completes(job_manager: JobManager):
    def op(job):
        with job.progress.step(0):
            pass
        return {"ok": True}

    job = job_manager.submit("Test Job", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    assert job.state in (JobState.QUEUED, JobState.RUNNING, JobState.COMPLETED)
    _wait_for(job)
    assert job.state == JobState.COMPLETED
    assert job.result == {"ok": True}
    assert job.error is None
    assert job.started_at is not None
    assert job.ended_at is not None


def test_submit_records_history_on_completion(job_manager: JobManager):
    def op(job):
        return "done"

    job = job_manager.submit("Test Job", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    _wait_for(job)
    record = _wait_for_history(job_manager, job.id)
    assert record is not None and record.state == "COMPLETED"


def test_failed_operation_marks_job_failed(job_manager: JobManager):
    def op(job):
        raise ValueError("boom")

    job = job_manager.submit("Failing Job", JobCategory.OPTIMIZATION, op, "Test Page", ["Step 1"])
    _wait_for(job)
    assert job.state == JobState.FAILED
    assert "boom" in job.error
    record = _wait_for_history(job_manager, job.id)
    assert record is not None and record.state == "FAILED"


def test_cancel_queued_job_never_runs(job_manager: JobManager):
    ran = []

    def blocker(job):
        time.sleep(0.3)
        return None

    def op(job):
        ran.append(True)
        return None

    blocking_job = job_manager.submit("Blocker", JobCategory.OPTIMIZATION, blocker, "Test Page", ["Step 1"])
    queued_job = job_manager.submit("Queued", JobCategory.OPTIMIZATION, op, "Test Page", ["Step 1"])
    time.sleep(0.05)
    assert queued_job.state == JobState.QUEUED

    cancelled = job_manager.cancel(queued_job.id)
    assert cancelled.state == JobState.CANCELLED
    _wait_for(blocking_job)
    assert ran == []


def test_cancel_running_job_cooperatively_via_progress_callback(job_manager: JobManager):
    def op(job):
        with job.progress.step(0):
            callback = job.progress.make_progress_callback(job)
            for i in range(50):
                callback(i, 50, "Working")
                time.sleep(0.01)
        return "finished"

    job = job_manager.submit("Cancellable Job", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    time.sleep(0.05)
    assert job.state == JobState.RUNNING
    job_manager.cancel(job.id)
    _wait_for(job)
    assert job.state == JobState.CANCELLED


def test_cancel_running_finds_the_running_job(job_manager: JobManager):
    def op(job):
        callback = job.progress.make_progress_callback(job)
        for i in range(50):
            callback(i, 50, "Working")
            time.sleep(0.01)
        return None

    job = job_manager.submit("Running Job", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    time.sleep(0.05)
    result = job_manager.cancel_running()
    assert result is not None
    assert result.id == job.id
    _wait_for(job)
    assert job.state == JobState.CANCELLED


def test_cancel_running_returns_none_when_nothing_running(job_manager: JobManager):
    assert job_manager.cancel_running() is None


def test_retry_resubmits_equivalent_job(job_manager: JobManager):
    calls = []

    def op(job):
        calls.append(1)
        return len(calls)

    job = job_manager.submit("Retryable", JobCategory.BACKTEST, op, "Test Page", ["Step 1"], metadata={"x": 1})
    _wait_for(job)
    assert job.result == 1

    retried = job_manager.retry(job.id)
    assert retried.id != job.id
    assert retried.name == job.name
    assert retried.category == job.category
    assert retried.metadata == {"x": 1}
    _wait_for(retried)
    assert retried.result == 2


def test_clear_finished_removes_terminal_jobs_only(job_manager: JobManager):
    def op(job):
        return None

    def blocker(job):
        time.sleep(0.3)
        return None

    finished_job = job_manager.submit("Finished", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    _wait_for(finished_job)
    running_job = job_manager.submit("Blocker", JobCategory.BACKTEST, blocker, "Test Page", ["Step 1"])
    time.sleep(0.05)

    cleared = job_manager.clear_finished()
    assert cleared == 1
    assert job_manager.get(finished_job.id) is None
    assert job_manager.get(running_job.id) is not None
    _wait_for(running_job)


def test_status_counts_reflect_queue_and_running_state(job_manager: JobManager):
    def blocker(job):
        time.sleep(0.2)
        return None

    def op(job):
        return None

    blocking_job = job_manager.submit("Blocker", JobCategory.BACKTEST, blocker, "Test Page", ["Step 1"])
    queued_job = job_manager.submit("Queued", JobCategory.BACKTEST, op, "Test Page", ["Step 1"])
    time.sleep(0.05)
    counts = job_manager.status_counts()
    assert counts["running_jobs"] == 1
    assert counts["queued_jobs"] == 1
    _wait_for(blocking_job)
    _wait_for(queued_job)


def test_get_returns_none_for_unknown_job(job_manager: JobManager):
    assert job_manager.get("does-not-exist") is None


def test_cancel_unknown_job_raises(job_manager: JobManager):
    from app.job_manager.exceptions import JobNotFoundError

    with pytest.raises(JobNotFoundError):
        job_manager.cancel("does-not-exist")
