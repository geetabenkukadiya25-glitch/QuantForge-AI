"""A global bottom status bar -- reads state a page already has (dataset
persistence via `app.ui.state`, and whatever execution/validation summary
the calling page already computed) and renders it as one caption row.
Never introduces new business logic or new state of its own.

Honest limitation: Streamlit has no API for a page-independent, truly
fixed/pinned footer (that would require a custom component); this renders
as a divider + caption row at the end of the page's own script, the same
"fixed-ratio approximation" spirit already documented for Strategy
Library's 3-column layout.
"""

from datetime import datetime
from typing import TYPE_CHECKING

import streamlit as st

from app.ui.state import has_dataset, load_metadata

if TYPE_CHECKING:
    from app.job_manager.job import Job


def render_status_bar(
    module: str,
    strategy_status: str = "—",
    validation_status: str = "—",
    execution_status: str = "Ready",
    progress_pct: float | None = None,
    elapsed_seconds: float | None = None,
    running_jobs: int | None = None,
    queued_jobs: int | None = None,
    completed_jobs_today: int | None = None,
    job: "Job | None" = None,
) -> None:
    """`running_jobs`/`queued_jobs`/`completed_jobs_today` are optional
    (Phase 18.4) -- pages that submit work through `JobManager` pass
    `**job_manager.status_counts()`; pages that don't (e.g. Strategy
    Library, Historical Data) simply omit them and the bar renders `—`
    for each, unchanged from before.

    `job` is optional (Phase 18.5): when omitted the bar renders exactly
    as before (a single static row). When a `Job` is passed, the bar
    additionally self-refreshes once a second via `st.fragment` and shows
    Current Stage, ETA, and Processing Rate/Current Candle alongside the
    existing Progress/Elapsed fields, sourced from that job's own
    `JobProgress` -- never a second progress system."""
    if job is None:
        _render_status_bar_body(module, strategy_status, validation_status, execution_status, progress_pct, elapsed_seconds, running_jobs, queued_jobs, completed_jobs_today)
    else:
        _render_status_bar_live(module, strategy_status, validation_status, execution_status, running_jobs, queued_jobs, completed_jobs_today, job.id)


def _render_status_bar_body(
    module: str,
    strategy_status: str,
    validation_status: str,
    execution_status: str,
    progress_pct: float | None,
    elapsed_seconds: float | None,
    running_jobs: int | None,
    queued_jobs: int | None,
    completed_jobs_today: int | None,
    extra_caption: str | None = None,
) -> None:
    dataset_status = "—"
    if has_dataset():
        metadata = load_metadata()
        dataset_status = metadata.filename if metadata is not None else "Loaded"

    progress_text = f"{progress_pct:.0f}%" if progress_pct is not None else "—"
    elapsed_text = f"{elapsed_seconds:,.1f}s" if elapsed_seconds is not None else "—"
    running_text = str(running_jobs) if running_jobs is not None else "—"
    queued_text = str(queued_jobs) if queued_jobs is not None else "—"
    completed_today_text = str(completed_jobs_today) if completed_jobs_today is not None else "—"

    st.divider()
    cols = st.columns(12)
    cols[0].caption(f"Module: **{module}**")
    cols[1].caption(f"Dataset: {dataset_status}")
    cols[2].caption(f"Strategy: {strategy_status}")
    cols[3].caption(f"Validation: {validation_status}")
    cols[4].caption(f"Execution: {execution_status}")
    cols[5].caption(f"Progress: {progress_text}")
    cols[6].caption(f"Elapsed: {elapsed_text}")
    cols[7].caption(f"Running Jobs: {running_text}")
    cols[8].caption(f"Queued Jobs: {queued_text}")
    cols[9].caption(f"Completed Today: {completed_today_text}")
    cols[10].caption("Offline Mode")
    cols[11].caption(datetime.now().strftime("%H:%M:%S"))
    if extra_caption:
        st.caption(extra_caption)


@st.fragment(run_every=1)
def _render_status_bar_live(
    module: str,
    strategy_status: str,
    validation_status: str,
    execution_status: str,
    running_jobs: int | None,
    queued_jobs: int | None,
    completed_jobs_today: int | None,
    job_id: str,
) -> None:
    if not st.session_state.get("qf_show_runtime_monitor", True):
        st.caption("Progress hidden. Use the Command Bar's \"Show Progress\" to bring it back.")
        return

    from app.job_manager import get_job_manager
    from app.ui.components._job_live import candle_progress_text, current_stage_name, eta_text, processing_rate_text

    manager = get_job_manager()
    job = manager.get(job_id)
    if job is None:
        _render_status_bar_body(module, strategy_status, validation_status, execution_status, None, None, running_jobs, queued_jobs, completed_jobs_today)
        return

    extra = (
        f"Stage: {current_stage_name(job)} · Candle: {candle_progress_text(job)} · "
        f"Rate: {processing_rate_text(job)} · ETA: {eta_text(job)}"
    )
    _render_status_bar_body(
        module, strategy_status, validation_status, execution_status,
        progress_pct=float(job.progress.percentage), elapsed_seconds=job.elapsed_seconds,
        running_jobs=running_jobs, queued_jobs=queued_jobs, completed_jobs_today=completed_jobs_today,
        extra_caption=extra,
    )
