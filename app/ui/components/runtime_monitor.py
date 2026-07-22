"""Institutional Runtime Monitor (Phase 18.5) -- a reusable, read-only
presentation component every long-running dashboard mounts in its
Information column instead of the ad-hoc "Execution Status" card.

Pure presentation: reuses the existing `JobManager`/`Job`/`JobProgress`/
`ProgressTracker` unchanged (no second progress system), self-refreshes
via `st.fragment(run_every=1)` (the same mechanism `job_panel.py` and
Strategy Library's autosave fragment already use -- no thread, no
polling service). Memory/CPU are the current Python process's own
figures via `psutil`, imported lazily so this is the only module in the
codebase that depends on it.
"""

import streamlit as st

from app.job_manager import get_job_manager
from app.ui.components._job_live import (
    candle_progress_text,
    current_stage_name,
    drain_job_notifications,
    elapsed_text,
    eta_text,
    notify_progress_milestones,
    processing_rate_text,
    rerun_once_on_terminal,
)


def _process_memory_cpu() -> tuple[str, str]:
    try:
        import psutil

        process = psutil.Process()
        rss_mb = process.memory_info().rss / (1024 * 1024)
        cpu_pct = process.cpu_percent(interval=None)
        return f"{rss_mb:,.1f} MB", f"{cpu_pct:.1f}%"
    except Exception:  # noqa: BLE001 -- Memory/CPU are diagnostic extras, never worth crashing the page over
        return "—", "—"


@st.fragment(run_every=1)
def _render_runtime_monitor_fragment(job_id: str, dataset_label: str | None, strategy_label: str | None) -> None:
    if not st.session_state.get("qf_show_runtime_monitor", True):
        st.caption("Progress hidden. Use the Command Bar's \"Show Progress\" to bring it back.")
        return

    manager = get_job_manager()
    job = manager.get(job_id)

    st.subheader("Runtime Monitor")
    counts = manager.status_counts()
    count_cols = st.columns(3)
    count_cols[0].metric("Running Jobs", counts["running_jobs"])
    count_cols[1].metric("Queued Jobs", counts["queued_jobs"])
    count_cols[2].metric("Completed Today", counts["completed_jobs_today"])

    if job is None:
        st.caption("No job found.")
        return

    rerun_once_on_terminal(job)
    drain_job_notifications(manager)
    notify_progress_milestones(job)

    st.progress(job.progress.percentage / 100)
    st.caption(f"{job.progress.percentage}%")

    memory_text, cpu_text = _process_memory_cpu()
    rows = [
        ("Current Stage", current_stage_name(job)),
        ("Current Candle", candle_progress_text(job)),
        ("Processing Rate", processing_rate_text(job)),
        ("Elapsed", elapsed_text(job)),
        ("ETA", eta_text(job)),
        ("Dataset", dataset_label or "—"),
        ("Strategy", strategy_label or "—"),
        ("Memory", memory_text),
        ("CPU", cpu_text),
        ("Status", job.state.value),
    ]
    for label, value in rows:
        cols = st.columns([1, 1])
        cols[0].caption(label)
        cols[1].caption(value)

    if job.error:
        st.error(job.error)


def render_runtime_monitor(job_id: str | None, dataset_label: str | None = None, strategy_label: str | None = None, container=None) -> None:
    """Mount the Runtime Monitor. `job_id=None` renders the idle/summary
    state (queue counts only, no fragment -- nothing to animate yet)."""
    target = container if container is not None else st
    with target.container(border=True):
        if job_id is None:
            st.subheader("Runtime Monitor")
            manager = get_job_manager()
            counts = manager.status_counts()
            count_cols = st.columns(3)
            count_cols[0].metric("Running Jobs", counts["running_jobs"])
            count_cols[1].metric("Queued Jobs", counts["queued_jobs"])
            count_cols[2].metric("Completed Today", counts["completed_jobs_today"])
            st.caption("Status: IDLE")
            return
        _render_runtime_monitor_fragment(job_id, dataset_label, strategy_label)
