"""`app.ui.components.status_bar`: the bottom status bar. The default
(no `job=`) path must stay byte-for-byte unchanged (Phase 18.2/18.3
backward compatibility across ~60 existing call sites); the new `job=`
path (Phase 18.5) additionally renders live Progress/Stage/ETA/Rate."""

import time

from streamlit.testing.v1 import AppTest

from app.job_manager import JobCategory, JobState, get_job_manager


def _render_default() -> None:
    from app.ui.components.status_bar import render_status_bar

    render_status_bar(module="Test Module", strategy_status="My Strategy", execution_status="Ready")


def test_default_call_renders_static_bar_unchanged() -> None:
    at = AppTest.from_function(_render_default)
    at.run()
    assert at.exception == []
    captions = [c.value for c in at.caption]
    assert any("Module: **Test Module**" in c for c in captions)
    assert any("Progress: —" in c for c in captions)
    assert any("Running Jobs: —" in c for c in captions)


def _wait_for_terminal(job_id: str, timeout: float = 10.0) -> None:
    manager = get_job_manager()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job is not None and job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            return
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not reach a terminal state within {timeout}s.")


def _render_with_job() -> None:
    import streamlit as st

    from app.ui.components.status_bar import render_status_bar
    from app.job_manager import get_job_manager

    job_id = st.session_state["_test_job_id"]
    job = get_job_manager().get(job_id)
    render_status_bar(module="Test Module", strategy_status="My Strategy", execution_status="Running", job=job)


def test_job_call_renders_live_extra_fields() -> None:
    def _operation(job):
        with job.progress.step(0):
            job.progress.make_progress_callback(job)(3, 10, "Processing")
        return "ok"

    job = get_job_manager().submit(
        name="Status bar test job",
        category=JobCategory.BACKTEST,
        operation=_operation,
        owner_page="test_status_bar",
        step_names=["Only Step"],
    )
    _wait_for_terminal(job.id)

    at = AppTest.from_function(_render_with_job)
    at.session_state["_test_job_id"] = job.id
    at.run()
    assert at.exception == []

    captions = " ".join(c.value for c in at.caption)
    assert "Stage:" in captions
    assert "Candle:" in captions
    assert "Rate:" in captions
    assert "ETA:" in captions
    assert "100%" in captions  # completed job's percentage
