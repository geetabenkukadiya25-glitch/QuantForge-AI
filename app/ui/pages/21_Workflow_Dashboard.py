"""
Streamlit page: Workflow Dashboard.

The central UI for Workflow Orchestration (Phase 17.6) -- chains existing
modules (Dataset Manager, Strategy Library, Job Manager, Data Catalog)
into reusable research pipelines. Every step still submits an ordinary
Job Manager job; this page never calls an engine directly and never
duplicates Dataset Manager / Strategy Library / Data Catalog / Job
Manager. Workflow execution is entirely optional -- every existing
dashboard continues to work unchanged whether or not this page is used.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page (Dataset Manager, Data Catalog), following the same
list-select pattern rather than a live in-place editor.
"""

import json

import streamlit as st

from app.workflow import StepType, WorkflowStatus, get_workflow_manager, is_valid_transition
from app.workflow.exceptions import InvalidStateTransitionError, WorkflowValidationError
from app.workflow.workflow_graph import build_tree
from app.workflow.workflow_step import WorkflowStep
from app.workflow.workflow_template import TEMPLATES
from app.workflow.workflow_validator import validate_template
from app.ui.components import (
    ToolbarAction,
    notify,
    render_command_bar,
    render_info_card,
    render_notification_center,
    render_shell,
    render_status_bar,
    render_toolbar,
)

st.set_page_config(page_title="Workflow Dashboard - QuantForge AI", page_icon="🧭", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Workflow Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Workflow Dashboard")
st.caption(
    "Chain Dataset Manager, Strategy Library, and every research engine into a reusable pipeline. "
    "Every step still runs as an ordinary Job Manager job -- this page never calls an engine directly."
)

manager = get_workflow_manager()


def _job_manager_status_counts() -> dict:
    from app.job_manager import get_job_manager

    return get_job_manager().status_counts()


st.session_state.setdefault("wf_selected_id", None)
st.session_state.setdefault("wf_delete_armed", False)
st.session_state.setdefault("wf_current_run_id", None)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    explorer_tab, templates_tab = st.tabs(["Explorer", "Templates"])

    with explorer_tab:
        if st.button("➕ New Workflow", key="wf_new", use_container_width=True):
            workflow = manager.create(name=f"New Workflow {len(manager.list_entries(archived=None)) + 1}")
            st.session_state.wf_selected_id = workflow.id
            notify("success", f"Created '{workflow.name}'.")
            st.rerun()

        query = st.text_input("Search", key="wf_search_query", placeholder="Name, description, tag...")

        def _render_workflow_list(workflows, list_key: str) -> None:
            if not workflows:
                st.caption("Nothing here.")
                return
            for workflow in workflows:
                with st.container(border=True):
                    is_selected = st.session_state.wf_selected_id == workflow.id
                    star = "⭐ " if workflow.favorite else ""
                    lock = "🔒 " if workflow.protected else ""
                    st.markdown(f"{'▶ ' if is_selected else ''}{star}{lock}**{workflow.name}**")
                    st.caption(f"{workflow.status.value} · {len(workflow.steps)} step(s)")
                    if st.button("Select", key=f"wf_select_{list_key}_{workflow.id}", use_container_width=True, disabled=is_selected):
                        st.session_state.wf_selected_id = workflow.id
                        st.rerun()

        all_tab, favorites_tab, archive_tab = st.tabs(["All", "Favorites", "Archive"])
        workflows = manager.search(query) if query.strip() else manager.list_entries(archived=False)
        with all_tab:
            _render_workflow_list(workflows, "all")
        with favorites_tab:
            _render_workflow_list([w for w in workflows if w.favorite], "favorites")
        with archive_tab:
            _render_workflow_list(manager.list_entries(archived=True), "archive")

    with templates_tab:
        st.caption("Built-in pipelines -- fill in dataset/strategy parameters in the Editor after creating one.")
        for template_name in TEMPLATES:
            with st.container(border=True):
                st.markdown(f"**{template_name}**")
                if st.button("Use Template", key=f"wf_template_{template_name}", use_container_width=True):
                    workflow = manager.from_template(template_name)
                    st.session_state.wf_selected_id = workflow.id
                    notify("success", f"Created '{workflow.name}' from template.")
                    st.rerun()

with workspace_col:
    selected_id = st.session_state.wf_selected_id
    selected = manager.get(selected_id) if selected_id else None
    current_run = manager.get_run(st.session_state.wf_current_run_id) if st.session_state.wf_current_run_id else None
    run_active = current_run is not None and current_run.status in (WorkflowStatus.QUEUED, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=selected is not None and not run_active, disabled_reason="A run is already active." if run_active else (None if selected else "Select a workflow first.")),
            ToolbarAction("⏸ Pause", "pause", enabled=run_active and current_run.status == WorkflowStatus.RUNNING, disabled_reason=None if (run_active and current_run.status == WorkflowStatus.RUNNING) else "No running run to pause."),
            ToolbarAction("⏵ Resume", "resume", enabled=run_active and current_run.status == WorkflowStatus.PAUSED, disabled_reason=None if (run_active and current_run.status == WorkflowStatus.PAUSED) else "No paused run to resume."),
            ToolbarAction("⏹ Cancel", "cancel", enabled=run_active, disabled_reason=None if run_active else "No active run to cancel."),
            ToolbarAction("↻ Retry", "retry", enabled=current_run is not None and not run_active, disabled_reason=None if (current_run is not None and not run_active) else "No finished run to retry."),
            ToolbarAction("⧉ Duplicate", "duplicate", enabled=selected is not None, disabled_reason=None if selected else "Select a workflow first."),
            ToolbarAction("🗄 Archive" if not (selected and selected.archived) else "↩ Restore", "archive_toggle", enabled=selected is not None, disabled_reason=None if selected else "Select a workflow first."),
            ToolbarAction("🗑 Delete", "delete", enabled=selected is not None and not selected.protected, disabled_reason="Protected workflows cannot be deleted." if (selected and selected.protected) else (None if selected else "Select a workflow first.")),
        ]
    )

    if selected is not None:
        if toolbar_clicked.get("run"):
            try:
                run = manager.submit_run(selected.id)
            except (WorkflowValidationError, InvalidStateTransitionError) as exc:
                notify("error", f"Cannot run: {exc}")
            else:
                st.session_state.wf_current_run_id = run.id
                notify("info", f"Queued run for '{selected.name}'.")
                st.rerun()
        if toolbar_clicked.get("pause") and current_run is not None:
            manager.pause(current_run.id)
            notify("warning", "Pause requested.")
            st.rerun()
        if toolbar_clicked.get("resume") and current_run is not None:
            manager.resume(current_run.id)
            notify("info", "Resume requested.")
            st.rerun()
        if toolbar_clicked.get("cancel") and current_run is not None:
            manager.cancel(current_run.id)
            notify("warning", "Cancel requested.")
            st.rerun()
        if toolbar_clicked.get("retry") and current_run is not None:
            # Re-submits the whole workflow from its persisted step
            # definitions -- see `WorkflowManager.retry_step`'s docstring
            # for why a full re-run (not a mid-flight resume) is the
            # honest behavior here.
            try:
                run = manager.submit_run(selected.id)
            except (WorkflowValidationError, InvalidStateTransitionError) as exc:
                notify("error", f"Cannot retry: {exc}")
            else:
                st.session_state.wf_current_run_id = run.id
                notify("info", "Retrying workflow.")
                st.rerun()
        if toolbar_clicked.get("duplicate"):
            dup = manager.duplicate(selected.id)
            st.session_state.wf_selected_id = dup.id
            notify("success", f"Duplicated as '{dup.name}'.")
            st.rerun()
        if toolbar_clicked.get("archive_toggle"):
            try:
                if selected.archived:
                    manager.restore(selected.id)
                    notify("info", f"Restored '{selected.name}'.")
                else:
                    manager.archive(selected.id)
                    notify("info", f"Archived '{selected.name}'.")
            except InvalidStateTransitionError as exc:
                notify("error", str(exc))
            st.rerun()
        if toolbar_clicked.get("delete"):
            st.session_state.wf_delete_armed = True

    if selected is None:
        st.info("Select a workflow in the Explorer, or create one from a Template.")
        render_status_bar(module="Workflow Dashboard", execution_status="Ready", **_job_manager_status_counts())
        st.stop()

    if st.session_state.wf_delete_armed:
        st.warning(f"Delete '{selected.name}'? This cannot be undone.")
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Delete", type="primary"):
            try:
                manager.delete(selected.id)
            except InvalidStateTransitionError as exc:
                st.error(str(exc))
            else:
                st.session_state.wf_selected_id = None
                st.session_state.wf_delete_armed = False
                notify("warning", f"Deleted '{selected.name}'.")
                st.rerun()
        if confirm_cols[1].button("Cancel"):
            st.session_state.wf_delete_armed = False
            st.rerun()

    editor_tab, timeline_tab, queue_tab, history_tab, audit_tab, statistics_tab, graph_tab = st.tabs(
        ["Editor", "Execution Timeline", "Queue", "History", "Audit", "Statistics", "Dependency Graph"]
    )

    with editor_tab:
        with st.form("wf_meta_form"):
            name = st.text_input("Name", value=selected.name)
            description = st.text_area("Description", value=selected.description)
            tags = st.text_input("Tags (comma-separated)", value=", ".join(selected.tags))
            submitted = st.form_submit_button("Save Workflow Metadata")
            if submitted:
                manager.update(selected.id, name=name, description=description, tags=[t.strip() for t in tags.split(",") if t.strip()])
                notify("success", "Workflow metadata saved.")
                st.rerun()

        st.markdown("**Steps**")
        for step in selected.steps:
            with st.expander(f"{step.display_name} ({step.type.value}) -- {step.id}"):
                with st.form(f"wf_step_form_{step.id}"):
                    display_name = st.text_input("Display name", value=step.display_name, key=f"wf_step_name_{step.id}")
                    enabled = st.checkbox("Enabled", value=step.enabled, key=f"wf_step_enabled_{step.id}")
                    timeout = st.number_input("Timeout (seconds, 0 = none)", value=float(step.timeout or 0), min_value=0.0, key=f"wf_step_timeout_{step.id}")
                    retry_count = st.number_input("Retry count", value=step.retry_count, min_value=0, step=1, key=f"wf_step_retry_{step.id}")
                    continue_on_failure = st.checkbox("Continue on failure", value=step.continue_on_failure, key=f"wf_step_cof_{step.id}")
                    parameters_text = st.text_area("Parameters (JSON)", value=json.dumps(step.parameters, indent=2), height=150, key=f"wf_step_params_{step.id}")
                    step_submitted = st.form_submit_button("Save Step")
                    if step_submitted:
                        try:
                            parameters = json.loads(parameters_text) if parameters_text.strip() else {}
                        except json.JSONDecodeError as exc:
                            st.error(f"Invalid JSON: {exc}")
                        else:
                            step.display_name = display_name
                            step.enabled = enabled
                            step.timeout = timeout or None
                            step.retry_count = int(retry_count)
                            step.continue_on_failure = continue_on_failure
                            step.parameters = parameters
                            manager.update(selected.id, steps=selected.steps)
                            notify("success", f"Step '{display_name}' saved.")
                            st.rerun()

        with st.expander("➕ Add step"):
            new_type = st.selectbox("Step type", [t.value for t in StepType], key="wf_new_step_type")
            new_name = st.text_input("Display name", value=new_type.title(), key="wf_new_step_name")
            depends_on = st.multiselect("Depends on", [s.id for s in selected.steps], key="wf_new_step_deps")
            if st.button("Add Step", key="wf_add_step"):
                step = WorkflowStep(type=StepType(new_type), display_name=new_name)
                new_steps = selected.steps + [step]
                new_deps = dict(selected.dependencies)
                if depends_on:
                    new_deps[step.id] = list(depends_on)
                manager.update(selected.id, steps=new_steps, dependencies=new_deps)
                notify("success", f"Added step '{new_name}'.")
                st.rerun()

        issues = validate_template(selected)
        if issues:
            st.error("Validation issues:\n\n" + "\n".join(f"- {i}" for i in issues))
        else:
            st.success("Workflow is structurally valid.")

    with timeline_tab:
        if current_run is None:
            st.caption("No run yet -- click Run in the toolbar.")
        else:
            st.metric("Run Status", current_run.status.value)
            if current_run.error:
                st.error(current_run.error)
            steps_by_id = {s.id: s for s in selected.steps}
            for step_id, result in current_run.step_results.items():
                step_label = steps_by_id[step_id].display_name if step_id in steps_by_id else step_id
                icon = {"COMPLETED": "✅", "FAILED": "❌", "CANCELLED": "⏹", "SKIPPED": "⏭", "TIMED_OUT": "⏱"}.get(result.state.value, "⏳")
                st.markdown(f"{icon} **{step_label}** — {result.state.value}" + (f" — {result.error}" if result.error else ""))
            if run_active:
                st.caption("This tab reflects the last page refresh -- click Refresh in the Command Bar or reload to see live progress.")

    with queue_tab:
        active_runs = manager.list_runs(selected.id)
        if not active_runs:
            st.caption("No active runs.")
        else:
            st.dataframe(
                [{"Run ID": r.id, "Status": r.status.value, "Started": r.started_at.isoformat(timespec="seconds") if r.started_at else "—"} for r in active_runs],
                use_container_width=True,
                hide_index=True,
            )

    with history_tab:
        history = manager.run_history(selected.id)
        if not history:
            st.caption("No finished runs yet.")
        else:
            st.dataframe(
                [
                    {
                        "Run ID": r.id,
                        "Status": r.status.value,
                        "Started": r.started_at.isoformat(timespec="seconds") if r.started_at else "—",
                        "Duration (s)": f"{r.duration_seconds:.1f}" if r.duration_seconds is not None else "—",
                        "Error": r.error or "—",
                    }
                    for r in history
                ],
                use_container_width=True,
                hide_index=True,
            )

    with audit_tab:
        events = manager.list_audit_events(selected.id)
        if not events:
            st.caption("No audit events yet.")
        else:
            st.dataframe(
                [{"Event": e.event_type.value, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in events],
                use_container_width=True,
                hide_index=True,
            )

    with statistics_tab:
        history = manager.run_history(selected.id, limit=500)
        completed = [r for r in history if r.status == WorkflowStatus.COMPLETED]
        failed = [r for r in history if r.status == WorkflowStatus.FAILED]
        durations = [r.duration_seconds for r in history if r.duration_seconds is not None]
        cols = st.columns(4)
        cols[0].metric("Total Runs", len(history))
        cols[1].metric("Completed", len(completed))
        cols[2].metric("Failed", len(failed))
        cols[3].metric("Avg Duration (s)", f"{sum(durations) / len(durations):.1f}" if durations else "—")

    with graph_tab:
        tree = build_tree(selected.steps, selected.dependencies)

        def _render_node(node: dict, depth: int = 0) -> None:
            step = node["step"]
            with st.expander(f"{'    ' * depth}{step.display_name} ({step.type.value})", expanded=True):
                st.caption(f"id: {step.id} · enabled: {step.enabled}")
                for child in node["children"]:
                    _render_node(child, depth + 1)

        if not tree:
            st.caption("No steps yet.")
        for root in tree:
            _render_node(root)

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card(
            "General",
            [
                ("Name", selected.name),
                ("Status", selected.status.value),
                ("Version", selected.version),
                ("Favorite", "Yes" if selected.favorite else "No"),
                ("Archived", "Yes" if selected.archived else "No"),
            ],
        )
        fav_label = "☆ Unfavorite" if selected.favorite else "⭐ Favorite"
        if st.button(fav_label, key="wf_toggle_favorite", use_container_width=True):
            manager.toggle_favorite(selected.id)
            st.rerun()
        render_info_card("Steps", [("Total steps", len(selected.steps)), ("Enabled steps", sum(1 for s in selected.steps if s.enabled))])
        render_info_card("Dependencies", [("Declared dependencies", sum(len(v) for v in selected.dependencies.values()))])
        if current_run is not None:
            render_info_card(
                "Last Run",
                [("Run ID", current_run.id), ("Status", current_run.status.value), ("Duration (s)", f"{current_run.duration_seconds:.1f}" if current_run.duration_seconds is not None else "—")],
            )
        history_count = len(manager.run_history(selected.id, limit=500))
        render_info_card("Statistics", [("Total runs", history_count)])
        render_info_card("Audit", [("Total events", len(manager.list_audit_events(selected.id)))])
    else:
        st.caption("Select a workflow in the Explorer to see its details.")

render_status_bar(
    module="Workflow Dashboard",
    execution_status="Ready" if selected is None else (current_run.status.value if current_run else selected.status.value),
    **_job_manager_status_counts(),
)
