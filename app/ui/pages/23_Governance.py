"""
Streamlit page: Governance.

The central UI for Institutional Research Governance (Phase 17.8) --
approval/review lifecycle and compliance reporting over already-existing
objects (Strategy, Dataset, Workflow, Risk Report, Experiment, Research
Report, Export, Portfolio). This page never executes anything and never
modifies any governed object; it only reads objects by id and writes its
own separate `GovernanceRecord`/`GovernancePolicy` state. Long-running
compliance sweeps run as an ordinary Job Manager job.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `gov_*` session-state prefix.
"""

import streamlit as st

from app.governance import GovernanceStatus, GovernedObjectType, Role, get_governance_manager
from app.governance.exceptions import GovernanceError
from app.governance.permissions import can
from app.governance.policies import is_approval_required
from app.governance.review import decision_history
from app.job_manager import JobState, get_job_manager
from app.ui.components import (
    ToolbarAction,
    notify,
    render_command_bar,
    render_info_card,
    render_notification_center,
    render_runtime_monitor,
    render_shell,
    render_status_bar,
    render_toolbar,
)

st.set_page_config(page_title="Governance - QuantForge AI", page_icon="🛡", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Governance")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Governance")
st.caption(
    "Institutional Research Governance -- approval/review lifecycle and compliance reporting over already-existing "
    "objects. Read/reference-only: this page never executes a workflow, never recomputes a risk metric, and never "
    "modifies any governed object."
)

manager = get_governance_manager()
job_manager = get_job_manager()

st.session_state.setdefault("gov_selected_id", None)
st.session_state.setdefault("gov_delete_armed", False)
st.session_state.setdefault("gov_current_job_id", None)
st.session_state.setdefault("gov_role", Role.ADMIN.value)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    with st.expander("▶ New Governance Record"):
        object_type_choice = st.selectbox("Object Type", [t.value for t in GovernedObjectType], key="gov_new_object_type")
        object_id = st.text_input("Object ID", key="gov_new_object_id", help="Strategy: library path string. Dataset/Workflow/Risk Report: their id. Experiment/Research Report/Export/Portfolio: a free-form label (see Known Limitations -- these have no durable id today).")
        object_label = st.text_input("Label (optional -- auto-resolved when possible)", key="gov_new_object_label")
        author = st.text_input("Author", value="researcher", key="gov_new_author")
        if st.button("Create Record", key="gov_create_record", disabled=not object_id.strip()):
            record = manager.create_record(
                GovernedObjectType(object_type_choice),
                object_id.strip(),
                object_label=object_label.strip() or None,
                author=author.strip() or None,
            )
            st.session_state.gov_selected_id = record.id
            notify("info", f"Created governance record for '{record.object_label}'.")
            st.rerun()

    type_filter = st.selectbox("Filter by type", ["(all)"] + [t.value for t in GovernedObjectType], key="gov_type_filter")
    status_filter = st.selectbox("Filter by status", ["(all)"] + [s.value for s in GovernanceStatus], key="gov_status_filter")

    records = manager.list_entries(
        object_type=GovernedObjectType(type_filter) if type_filter != "(all)" else None,
        status=GovernanceStatus(status_filter) if status_filter != "(all)" else None,
    )
    if not records:
        st.caption("No governance records yet -- create one above.")
    for record in records:
        with st.container(border=True):
            is_selected = st.session_state.gov_selected_id == record.id
            st.markdown(f"{'▶ ' if is_selected else ''}**{record.object_label or record.object_id}**")
            st.caption(f"{record.object_type.value} · {record.status.value}")
            if st.button("Select", key=f"gov_select_{record.id}", use_container_width=True, disabled=is_selected):
                st.session_state.gov_selected_id = record.id
                st.rerun()

    st.divider()
    if st.button("Run Compliance Report", key="gov_run_compliance"):
        job = manager.run_compliance_report()
        st.session_state.gov_current_job_id = job.id
        notify("info", f"Queued: {job.name}")
        st.rerun()

    current_job = job_manager.get(st.session_state.gov_current_job_id) if st.session_state.gov_current_job_id else None
    if current_job is not None and current_job.state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
        render_runtime_monitor(current_job.id)
    elif current_job is not None and current_job.state == JobState.COMPLETED:
        st.session_state.gov_last_compliance_report = current_job.result.to_dict()
        st.session_state.gov_current_job_id = None
        st.rerun()
    elif current_job is not None and current_job.state == JobState.FAILED:
        st.error(f"Compliance report failed: {current_job.error}")

with workspace_col:
    role = Role(st.session_state.gov_role)
    selected_id = st.session_state.gov_selected_id
    selected = manager.get(selected_id) if selected_id else None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("📝 Submit for Review", "submit", enabled=selected is not None and can(role, "submit_for_review"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("✅ Approve", "approve", enabled=selected is not None and can(role, "approve"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("❌ Reject", "reject", enabled=selected is not None and can(role, "reject"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("🔄 Request Changes", "request_changes", enabled=selected is not None and can(role, "request_changes"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("↩ Reopen", "reopen", enabled=selected is not None and can(role, "reopen"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("📦 Archive", "archive", enabled=selected is not None and can(role, "archive"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("📢 Publish", "publish", enabled=selected is not None and can(role, "publish"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("🔒 Lock / 🔓 Unlock", "toggle_lock", enabled=selected is not None and can(role, "lock"), disabled_reason=None if selected else "Select a record first."),
            ToolbarAction("🗑 Delete", "delete", enabled=selected is not None and can(role, "delete"), disabled_reason=None if selected else "Select a record first."),
        ]
    )

    if selected is not None:
        try:
            if toolbar_clicked.get("submit"):
                manager.submit_for_review(selected.id)
                notify("info", f"Submitted '{selected.object_label}' for review.")
                st.rerun()
            if toolbar_clicked.get("approve"):
                manager.approve(selected.id)
                notify("info", f"Approved '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("reject"):
                manager.reject(selected.id)
                notify("warning", f"Rejected '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("request_changes"):
                manager.request_changes(selected.id)
                notify("info", f"Requested changes on '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("reopen"):
                manager.reopen(selected.id)
                notify("info", f"Reopened '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("archive"):
                manager.archive(selected.id)
                notify("info", f"Archived '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("publish"):
                manager.publish(selected.id)
                notify("info", f"Published '{selected.object_label}'.")
                st.rerun()
            if toolbar_clicked.get("toggle_lock"):
                if selected.locked:
                    manager.unlock(selected.id)
                    notify("info", f"Unlocked '{selected.object_label}'.")
                else:
                    manager.lock(selected.id)
                    notify("info", f"Locked '{selected.object_label}'.")
                st.rerun()
        except GovernanceError as exc:
            notify("error", str(exc))

    if selected is not None and toolbar_clicked.get("delete"):
        st.session_state.gov_delete_armed = True

    if st.session_state.gov_delete_armed and selected is not None:
        st.warning(f"Delete governance record for '{selected.object_label}'? This cannot be undone.")
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Delete", type="primary"):
            try:
                manager.delete(selected.id)
            except GovernanceError as exc:
                notify("error", str(exc))
            else:
                st.session_state.gov_selected_id = None
                notify("warning", f"Deleted governance record for '{selected.object_label}'.")
            st.session_state.gov_delete_armed = False
            st.rerun()
        if confirm_cols[1].button("Cancel"):
            st.session_state.gov_delete_armed = False
            st.rerun()

    if selected is None:
        st.info("Select a governance record in the Explorer, or create a new one.")
        render_status_bar(module="Governance", execution_status="Ready", **job_manager.status_counts())
        st.stop()

    tabs = st.tabs(["Overview", "Approvals", "Reviews", "Policies", "Compliance", "Audit", "History", "Reports"])
    overview_tab, approvals_tab, reviews_tab, policies_tab, compliance_tab, audit_tab, history_tab, reports_tab = tabs

    with overview_tab:
        cols = st.columns(4)
        cols[0].metric("Status", selected.status.value)
        cols[1].metric("Revision", selected.revision_count)
        cols[2].metric("Locked", "Yes" if selected.locked else "No")
        cols[3].metric("Reviews", len(selected.review_history))
        st.markdown(f"**Object Type:** {selected.object_type.value}")
        st.markdown(f"**Object ID:** {selected.object_id}")
        st.markdown(f"**Author:** {selected.author or '—'}")
        st.markdown(f"**Tags:** {', '.join(selected.tags) if selected.tags else '—'}")
        st.markdown(f"**Created:** {selected.created_at.isoformat(timespec='seconds')}")
        st.markdown(f"**Updated:** {selected.updated_at.isoformat(timespec='seconds')}")

    with approvals_tab:
        approvals = [e for e in selected.review_history if e.decision.value in ("APPROVED", "REJECTED", "PUBLISHED")]
        if not approvals:
            st.caption("No approval decisions recorded yet.")
        else:
            st.dataframe(
                [{"Decision": e.decision.value, "Reviewer": e.reviewer, "Notes": e.notes, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in approvals],
                use_container_width=True,
                hide_index=True,
            )

    with reviews_tab:
        with st.form("gov_comment_form", clear_on_submit=True):
            comment_reviewer = st.text_input("Reviewer", value="reviewer")
            comment_notes = st.text_area("Comment")
            if st.form_submit_button("Add Comment") and comment_notes.strip():
                manager.add_comment(selected.id, comment_reviewer.strip() or "reviewer", comment_notes.strip())
                notify("info", "Comment added.")
                st.rerun()

        history = decision_history(selected)
        if not history:
            st.caption("No review notes yet.")
        else:
            st.dataframe(
                [{"Decision": e.decision.value, "Reviewer": e.reviewer, "Notes": e.notes, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in history],
                use_container_width=True,
                hide_index=True,
            )

    with policies_tab:
        policy = manager.get_policy()
        with st.form("gov_policy_form"):
            dataset_required = st.checkbox("Dataset Approval Required", value=policy.dataset_approval_required)
            strategy_required = st.checkbox("Strategy Approval Required", value=policy.strategy_approval_required)
            workflow_required = st.checkbox("Workflow Approval Required", value=policy.workflow_approval_required)
            risk_required = st.checkbox("Risk Approval Required", value=policy.risk_approval_required)
            report_required = st.checkbox("Report Approval Required", value=policy.report_approval_required)
            if st.form_submit_button("Save Policy"):
                manager.update_policy(
                    dataset_approval_required=dataset_required,
                    strategy_approval_required=strategy_required,
                    workflow_approval_required=workflow_required,
                    risk_approval_required=risk_required,
                    report_approval_required=report_required,
                )
                notify("info", "Policy updated.")
                st.rerun()
        st.caption(f"Policy exceptions: {', '.join(sorted(policy.exceptions)) if policy.exceptions else 'none'}")

    with compliance_tab:
        last_report = st.session_state.get("gov_last_compliance_report")
        if not last_report:
            st.caption("No compliance report generated yet -- click 'Run Compliance Report' in the Explorer.")
        else:
            compliance = last_report.get("sections", {}).get("compliance", {})
            cols = st.columns(3)
            cols[0].metric("Total Records", compliance.get("total_records", 0))
            cols[1].metric("Compliant", compliance.get("compliant_count", 0))
            cols[2].metric("Non-Compliant", compliance.get("non_compliant_count", 0))
            violations = compliance.get("violations", [])
            st.markdown("**Violations**")
            st.dataframe(violations, use_container_width=True, hide_index=True) if violations else st.caption("No violations.")

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

    with history_tab:
        records = manager.record_history(selected.id)
        if not records:
            st.caption("No status-change history yet.")
        else:
            st.dataframe(
                [{"Status": r.status.value, "Revision": r.revision_count, "Updated": r.updated_at.isoformat(timespec="seconds")} for r in records],
                use_container_width=True,
                hide_index=True,
            )

    with reports_tab:
        last_report = st.session_state.get("gov_last_compliance_report")
        if not last_report:
            st.caption("No governance report generated yet -- run a compliance report from the Explorer.")
        else:
            st.markdown(f"**Kind:** {last_report.get('kind')}")
            st.markdown(f"**Title:** {last_report.get('title')}")
            st.markdown(f"**Generated:** {last_report.get('created_at')}")
            st.json(last_report.get("sections", {}))

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card("General", [("Label", selected.object_label or "—"), ("Type", selected.object_type.value), ("Status", selected.status.value)])
        render_info_card("Object", [("Object ID", selected.object_id), ("Author", selected.author or "—")])
        render_info_card("Review Status", [("Revision Count", selected.revision_count), ("Locked", "Yes" if selected.locked else "No"), ("Reviews", len(selected.review_history))])
        policy = manager.get_policy()
        render_info_card("Policy", [("Approval required", "Yes" if is_approval_required(policy, selected.object_type, selected.object_id) else "No")])
        render_info_card("Audit", [("Total events", len(manager.list_audit_events(selected.id)))])
    else:
        st.caption("Select a governance record in the Explorer to see its details.")

render_status_bar(
    module="Governance",
    execution_status="Ready" if selected is None else (selected.object_label or selected.object_id),
    **job_manager.status_counts(),
)
