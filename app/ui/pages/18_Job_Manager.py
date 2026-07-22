"""
Streamlit page: Job Manager.

The central UI for the Job Manager (Phase 18.4) -- every dashboard's
heavy operation is now submitted as a `Job` (`app.job_manager`) instead
of running inline; this page is where the Queue/Running/Completed/
Cancelled/Failed lists and the persisted History live, with Retry/Cancel/
Clear actions. This page never touches any engine directly -- it only
ever reads `Job` objects and `JobRecord` history entries that other pages
already produced via `JobManager.submit(...)`.

Built on the same 3-column Explorer/Workspace/Information shell,
toolbar, tabs, and notification/command-bar/status-bar conventions
already used by every other dashboard (Phase 18.2/18.3).
"""

import streamlit as st

from app.job_manager import JobCategory, JobState, get_job_manager
from app.job_manager.job_state import is_terminal
from app.ui.components import (
    ToolbarAction,
    render_command_bar,
    render_info_card,
    render_job_panel,
    render_notification_center,
    render_shell,
    render_status_bar,
    render_toolbar,
)

st.set_page_config(page_title="Job Manager - QuantForge AI", page_icon="🗂️", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Job Manager")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Job Manager")
st.caption(
    "Central queue, run, cancel, retry, and history for every heavy dashboard operation. "
    "This page never calls any engine directly -- it only orchestrates jobs other pages submitted."
)

manager = get_job_manager()

st.session_state.setdefault("jm_selected_job_id", None)
st.session_state.setdefault("jm_default_tab", "Queue")

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    category_filter = st.selectbox("Category", ["All"] + [c.value for c in JobCategory])
    state_filter = st.selectbox("State", ["All"] + [s.value for s in JobState])

    all_jobs = manager.list(
        category=JobCategory(category_filter) if category_filter != "All" else None,
        state=JobState(state_filter) if state_filter != "All" else None,
    )
    st.caption(f"{len(all_jobs)} job(s)")

    for job in all_jobs:
        with st.container(border=True):
            is_selected = st.session_state.jm_selected_job_id == job.id
            st.markdown(f"{'▶ ' if is_selected else ''}**{job.name}**")
            st.caption(f"{job.category.value} · {job.state.value} · {job.owner_page}")
            if st.button("Select", key=f"jm_select_{job.id}", use_container_width=True, disabled=is_selected):
                st.session_state.jm_selected_job_id = job.id
                st.rerun()

with workspace_col:
    selected_job_id = st.session_state.jm_selected_job_id
    selected_job = manager.get(selected_job_id) if selected_job_id else None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction(
                "↻ Retry",
                "retry",
                enabled=selected_job is not None and is_terminal(selected_job.state),
                disabled_reason="Select a finished job to retry." if selected_job is None or not is_terminal(selected_job.state) else None,
            ),
            ToolbarAction(
                "✕ Cancel",
                "cancel",
                enabled=selected_job is not None and not is_terminal(selected_job.state),
                disabled_reason="Select a queued or running job to cancel." if selected_job is None or is_terminal(selected_job.state) else None,
            ),
            ToolbarAction("🗑 Clear Finished", "clear"),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("retry") and selected_job is not None:
        retried = manager.retry(selected_job.id)
        st.session_state.jm_selected_job_id = retried.id
        st.success(f"Retried '{selected_job.name}' as a new job.")
        st.rerun()
    if toolbar_clicked.get("cancel") and selected_job is not None:
        manager.cancel(selected_job.id)
        st.success(f"Cancel requested for '{selected_job.name}'.")
        st.rerun()
    if toolbar_clicked.get("clear"):
        cleared = manager.clear_finished()
        if st.session_state.jm_selected_job_id and manager.get(st.session_state.jm_selected_job_id) is None:
            st.session_state.jm_selected_job_id = None
        st.success(f"Cleared {cleared} finished job(s) from the visible list.")
        st.rerun()

    # `st.tabs` has no "pre-select a tab" API -- the closest honest
    # approximation to "Open History" deep-linking here is putting the
    # requested tab first (Streamlit always shows the first tab active).
    base_tab_names = ["Queue", "Running", "Completed", "Cancelled", "Failed", "History"]
    requested = st.session_state.jm_default_tab
    st.session_state.jm_default_tab = "Queue"  # only honor the deep-link once per navigation
    tab_names = [requested] + [n for n in base_tab_names if n != requested] if requested in base_tab_names else base_tab_names
    rendered_tabs = dict(zip(tab_names, st.tabs(tab_names)))
    queue_tab, running_tab, completed_tab, cancelled_tab, failed_tab, history_tab = (
        rendered_tabs["Queue"], rendered_tabs["Running"], rendered_tabs["Completed"],
        rendered_tabs["Cancelled"], rendered_tabs["Failed"], rendered_tabs["History"],
    )

    def _job_table(jobs) -> None:
        if not jobs:
            st.caption("Nothing here.")
            return
        st.dataframe(
            [
                {
                    "Name": j.name,
                    "Category": j.category.value,
                    "Owner Page": j.owner_page,
                    "Elapsed (s)": f"{j.elapsed_seconds:.1f}" if j.elapsed_seconds is not None else "—",
                    "Created": j.created_at.isoformat(timespec="seconds"),
                }
                for j in jobs
            ],
            use_container_width=True,
            hide_index=True,
        )

    with queue_tab:
        _job_table(manager.list(state=JobState.QUEUED))
    with running_tab:
        _job_table(manager.list(state=JobState.RUNNING))
    with completed_tab:
        _job_table(manager.list(state=JobState.COMPLETED))
    with cancelled_tab:
        _job_table(manager.list(state=JobState.CANCELLED))
    with failed_tab:
        _job_table(manager.list(state=JobState.FAILED))
    with history_tab:
        records = manager.history()
        if not records:
            st.caption("No history recorded yet.")
        else:
            st.dataframe(
                [
                    {
                        "Name": r.name,
                        "Category": r.category,
                        "State": r.state,
                        "Owner Page": r.owner_page,
                        "Elapsed (s)": f"{r.elapsed_seconds:.1f}" if r.elapsed_seconds is not None else "—",
                        "Ended": r.ended_at or "—",
                        "Error": r.error_message or "",
                    }
                    for r in records
                ],
                use_container_width=True,
                hide_index=True,
            )

with info_col:
    st.subheader("Information")
    if selected_job is not None:
        render_info_card(
            "Selected Job",
            [
                ("Name", selected_job.name),
                ("Category", selected_job.category.value),
                ("Owner Page", selected_job.owner_page),
            ],
        )
        render_job_panel(selected_job.id)
    else:
        st.caption("Select a job in the Explorer to see its details.")

status_counts = manager.status_counts()
render_status_bar(module="Job Manager", execution_status="Ready", **status_counts)
