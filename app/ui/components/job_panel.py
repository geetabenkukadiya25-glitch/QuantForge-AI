"""Renders a single job's live status in a page's Information column
(Phase 18.4). Reuses `Job.progress.render(...)`, which itself reuses the
existing, unmodified `ProgressTracker` -- never a second progress system.

Uses `st.fragment(run_every=1)` to self-refresh while the job is active,
mirroring the exact `@st.fragment(run_every=30)` autosave pattern already
verified in `app/ui/pages/3_Strategy_Library.py`, just at a 1-second
interval appropriate for live job progress.
"""

import streamlit as st

from app.job_manager import get_job_manager
from app.job_manager.job_state import JobState
from app.ui.components._job_live import drain_job_notifications, rerun_once_on_terminal


@st.fragment(run_every=1)
def _render_job_panel_fragment(job_id: str) -> None:
    manager = get_job_manager()
    job = manager.get(job_id)
    if job is None:
        st.caption("No job found.")
        return

    rerun_once_on_terminal(job)
    drain_job_notifications(manager)

    st.write(f"**{job.name}**")
    st.caption(f"{job.category.value} · {job.state.value}")
    elapsed = job.elapsed_seconds
    eta = job.eta_seconds
    st.caption(f"Elapsed: {elapsed:,.1f}s" if elapsed is not None else "Elapsed: —")
    st.caption(f"ETA: {eta:,.1f}s" if eta is not None else "ETA: —")
    if job.error:
        st.error(job.error)
    if job.state in (JobState.RUNNING, JobState.QUEUED):
        job.progress.render()


def render_job_panel(job_id: str | None, container=None) -> None:
    target = container if container is not None else st
    with target.container(border=True):
        if job_id is None:
            st.caption("No job submitted yet.")
            return
        _render_job_panel_fragment(job_id)
