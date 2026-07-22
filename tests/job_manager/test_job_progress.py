import pytest

from app.job_manager.exceptions import JobCancelledError
from app.job_manager.job_progress import JobProgress


class _FakeJob:
    def __init__(self) -> None:
        self.id = "fake-job-id"
        self.cancel_requested = False


def test_step_context_manager_starts_and_completes():
    progress = JobProgress(["Step A", "Step B"])
    with progress.step(0):
        assert progress.tracker.steps[0].status.value == "RUNNING"
    assert progress.tracker.steps[0].status.value == "COMPLETE"
    assert progress.percentage == 50


def test_make_progress_callback_forwards_to_tracker():
    progress = JobProgress(["Step A"])
    job = _FakeJob()
    callback = progress.make_progress_callback(job)
    with progress.step(0):
        callback(5, 10, "Working")
        assert progress.tracker.item_progress is not None
        assert progress.tracker.item_progress.current == 5


def test_make_progress_callback_raises_when_cancel_requested():
    progress = JobProgress(["Step A"])
    job = _FakeJob()
    callback = progress.make_progress_callback(job)
    job.cancel_requested = True
    with pytest.raises(JobCancelledError):
        callback(1, 10, "Working")


def test_render_does_not_raise(capsys):
    progress = JobProgress(["Step A"])
    with progress.step(0):
        progress.render()
