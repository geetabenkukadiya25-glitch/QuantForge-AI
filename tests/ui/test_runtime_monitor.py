"""`app.ui.components.runtime_monitor`: the institutional Runtime Monitor
(Phase 18.5). Reuses the real, process-wide `JobManager` singleton (the
same one every dashboard page already uses) -- submits a fast synthetic
job, waits for it to reach a terminal state via a short bounded poll
(never a fixed sleep), then renders the component via `AppTest` and
checks its fields."""

import time

from streamlit.testing.v1 import AppTest

from app.job_manager import JobCategory, JobState, get_job_manager


def _wait_for_terminal(job_id: str, timeout: float = 10.0) -> None:
    manager = get_job_manager()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job is not None and job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            return
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not reach a terminal state within {timeout}s.")


def _submit_fast_job(name: str) -> str:
    def _operation(job):
        with job.progress.step(0):
            job.progress.make_progress_callback(job)(5, 10, "Processing")
        return "ok"

    job = get_job_manager().submit(
        name=name,
        category=JobCategory.BACKTEST,
        operation=_operation,
        owner_page="test_runtime_monitor",
        step_names=["Only Step"],
    )
    _wait_for_terminal(job.id)
    return job.id


def _render_idle() -> None:
    from app.ui.components.runtime_monitor import render_runtime_monitor

    render_runtime_monitor(None)


def test_idle_state_has_no_job_id() -> None:
    at = AppTest.from_function(_render_idle)
    at.run()
    assert at.exception == []
    captions = [c.value for c in at.caption]
    assert any("Status: IDLE" in c for c in captions)


def _render_with_job() -> None:
    import streamlit as st

    from app.ui.components.runtime_monitor import render_runtime_monitor

    job_id = st.session_state["_test_job_id"]
    render_runtime_monitor(job_id, dataset_label="my_dataset.csv", strategy_label="My Strategy")


def test_live_job_renders_stage_candle_rate_memory_cpu() -> None:
    job_id = _submit_fast_job("Runtime Monitor test job")

    at = AppTest.from_function(_render_with_job)
    at.session_state["_test_job_id"] = job_id
    at.run()
    assert at.exception == []

    captions = " ".join(c.value for c in at.caption)
    assert "my_dataset.csv" in captions
    assert "My Strategy" in captions
    assert "MB" in captions  # Memory rendered as a real number, not "-"
    assert "%" in captions  # CPU rendered as a real number
    assert "COMPLETED" in captions.upper() or "Completed" in captions


def test_unknown_job_id_shows_no_job_found() -> None:
    def _render() -> None:
        from app.ui.components.runtime_monitor import render_runtime_monitor

        render_runtime_monitor("nonexistent-job-id")

    at = AppTest.from_function(_render)
    at.run()
    assert at.exception == []
    captions = [c.value for c in at.caption]
    assert any("No job found" in c for c in captions)
