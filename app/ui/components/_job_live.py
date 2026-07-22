"""Shared live-refresh helpers for Job Manager UI surfaces (Phase 18.5).

Private to `app/ui/components` -- not a page-facing component itself.
Factors out the pieces `job_panel.py`, `runtime_monitor.py`, and
`status_bar.py`'s live branch all need: draining `JobEvent`s into the
existing Notification Center, watching for progress-percentage
milestones, formatting a job's current stage/candle/rate, and bridging a
`st.fragment`'s 1-second tick into a single full-page rerun the instant a
job reaches a terminal state (since a fragment only ever re-runs itself,
never the rest of the page).
"""

import streamlit as st

from app.job_manager.job import Job
from app.job_manager.job_manager import JobManager
from app.job_manager.job_state import is_terminal
from app.ui.components.notifications import notify

_KIND_TO_NOTIFY_KIND = {
    "started": "info",
    "completed": "success",
    "cancelled": "warning",
    "failed": "error",
}

_MILESTONES = (25, 50, 75)


def format_duration(seconds: float) -> str:
    """`HH:MM:SS`, matching `ProgressTracker._format_duration`'s idiom."""
    seconds = max(0, round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, sec = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"


def current_stage_name(job: Job) -> str:
    tracker = job.progress.tracker
    index = tracker.current_step_number - 1
    if 0 <= index < tracker.total_steps:
        return tracker.steps[index].name
    return "—"


def candle_progress_text(job: Job) -> str:
    item = job.progress.tracker.item_progress
    if item is None:
        return "—"
    return f"{item.current:,} / {item.total:,}"


def processing_rate_text(job: Job) -> str:
    item = job.progress.tracker.item_progress
    if item is None or item.items_per_second is None:
        return "—"
    return f"{item.items_per_second:,.0f} candles/sec"


def elapsed_text(job: Job) -> str:
    elapsed = job.elapsed_seconds
    return format_duration(elapsed) if elapsed is not None else "—"


def eta_text(job: Job) -> str:
    eta = job.eta_seconds
    return format_duration(eta) if eta is not None else "—"


def drain_job_notifications(manager: JobManager) -> None:
    """Global (all-jobs) drain of new `JobEvent`s into the existing
    Notification Center, using one monotonic cursor so it's safe to call
    from multiple mounted fragments without duplicating notifications."""
    cursor_key = "qf_job_events_cursor"
    last_id = st.session_state.get(cursor_key, 0)
    new_events = manager.events_since(last_id)
    for event in new_events:
        notify(_KIND_TO_NOTIFY_KIND.get(event.kind, "info"), event.message)
    if new_events:
        st.session_state[cursor_key] = new_events[-1].id


def notify_progress_milestones(job: Job) -> None:
    """Fire a one-time notification the first time `job`'s percentage
    crosses 25/50/75 -- a pure presentation-layer threshold watch, since
    the Job Manager backend emits no percentage-milestone event itself."""
    seen_by_job: dict[str, set[int]] = st.session_state.setdefault("qf_job_pct_milestones", {})
    seen = seen_by_job.setdefault(job.id, set())
    pct = job.progress.percentage
    for milestone in _MILESTONES:
        if pct >= milestone and milestone not in seen:
            seen.add(milestone)
            notify("info", f"{job.name}: {milestone}% complete")


def rerun_once_on_terminal(job: Job | None) -> None:
    """Bridge a fragment's own refresh into a single full-page rerun the
    instant `job` reaches a terminal state, so toolbar Run/Stop buttons,
    the status bar, and any `st.stop()`-gated results section (all of
    which live outside the fragment) snap to the correct state
    immediately instead of waiting for the next user interaction.
    Guarded to fire exactly once per job -- never loops."""
    if job is None or not is_terminal(job.state):
        return
    seen_key = f"qf_job_terminal_seen_{job.id}"
    if st.session_state.get(seen_key):
        return
    st.session_state[seen_key] = True
    st.rerun()
