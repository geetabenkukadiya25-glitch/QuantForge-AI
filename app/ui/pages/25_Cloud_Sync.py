"""
Streamlit page: Cloud Sync.

The central UI for the Institutional Cloud Sync Foundation (Phase 17.9)
-- a future-ready abstraction layer that performs ZERO network I/O,
requires ZERO credentials, and stores ZERO secrets. Every provider is a
placeholder whose interface methods raise `NotImplementedError`; every
"sync" action here only creates or transitions a local metadata record.
This page never modifies any engine, Job Manager, Dataset Manager, Data
Catalog, Workflow, Risk Analytics, Governance, Settings Center, Strategy
Library, or SDL module.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `syn_*` session-state prefix.
"""

import streamlit as st

from app.cloud_sync import SyncKind, SyncOperationStatus, get_sync_manager
from app.cloud_sync.artifact import ArtifactKind
from app.cloud_sync.credentials import describe_credential_requirements
from app.cloud_sync.exceptions import CloudSyncError
from app.cloud_sync.snapshot import SnapshotKind
from app.cloud_sync.sync_conflict import ConflictResolutionPolicy
from app.job_manager import get_job_manager
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

st.set_page_config(page_title="Cloud Sync - QuantForge AI", page_icon="☁", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Cloud Sync")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Cloud Sync")
st.caption(
    "Institutional Cloud Sync Foundation -- a future-ready abstraction layer that is completely offline today. "
    "No network I/O, no credentials, no secrets anywhere on this page. Every provider is a registered placeholder "
    "whose actions raise 'not implemented.'"
)

manager = get_sync_manager()
job_manager = get_job_manager()

st.session_state.setdefault("syn_selected_operation_id", None)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    with st.expander("▶ Queue a Sync"):
        kind_choice = st.selectbox("Kind", [k.value for k in SyncKind if k not in (SyncKind.ARTIFACT, SyncKind.SNAPSHOT)], key="syn_new_kind")

        object_options: dict[str, str] = {}
        if kind_choice == SyncKind.DATASET.value:
            from app.dataset_manager import DatasetManager

            for record in DatasetManager().list_entries(archived=False):
                object_options[record.display_name] = record.id
        elif kind_choice == SyncKind.STRATEGY.value:
            from app.strategy_library import StrategyLibraryManager

            for entry in StrategyLibraryManager().list_entries():
                object_options[entry.name] = str(entry.path)
        elif kind_choice == SyncKind.WORKFLOW.value:
            from app.workflow import get_workflow_manager

            for workflow in get_workflow_manager().list_entries(archived=None):
                object_options[workflow.name] = workflow.id
        elif kind_choice == SyncKind.RISK_REPORT.value:
            from app.risk_analytics import get_risk_manager

            for report in get_risk_manager().list_reports():
                object_options[report.title] = report.id
        elif kind_choice == SyncKind.GOVERNANCE_RECORD.value:
            from app.governance import get_governance_manager

            for record in get_governance_manager().list_entries():
                object_options[record.object_label or record.object_id] = record.id

        if kind_choice == SyncKind.SETTINGS.value:
            if st.button("Queue Settings Sync", key="syn_queue_settings"):
                op = manager.sync_settings()
                st.session_state.syn_selected_operation_id = op.id
                notify("info", f"Queued sync for '{op.object_label}'.")
                st.rerun()
        elif object_options:
            selected_label = st.selectbox("Object", list(object_options.keys()), key="syn_new_object")
            if st.button("Queue Sync", key="syn_queue_object"):
                object_id = object_options[selected_label]
                op = {
                    SyncKind.DATASET.value: manager.sync_dataset,
                    SyncKind.STRATEGY.value: manager.sync_strategy,
                    SyncKind.WORKFLOW.value: manager.sync_workflow,
                    SyncKind.RISK_REPORT.value: manager.sync_risk_report,
                    SyncKind.GOVERNANCE_RECORD.value: manager.sync_governance_record,
                }[kind_choice](object_id)
                st.session_state.syn_selected_operation_id = op.id
                notify("info", f"Queued sync for '{op.object_label}'.")
                st.rerun()
        else:
            st.caption("No objects of this kind exist yet.")

    st.markdown("**Recent Sync Operations**")
    operations = manager.list_operations()
    if not operations:
        st.caption("No sync operations yet -- queue one above.")
    for operation in operations[:10]:
        with st.container(border=True):
            is_selected = st.session_state.syn_selected_operation_id == operation.id
            st.markdown(f"{'▶ ' if is_selected else ''}**{operation.object_label or operation.object_id}**")
            st.caption(f"{operation.kind.value} · {operation.status.value}")
            if st.button("Select", key=f"syn_select_{operation.id}", use_container_width=True, disabled=is_selected):
                st.session_state.syn_selected_operation_id = operation.id
                st.rerun()

with workspace_col:
    selected_id = st.session_state.syn_selected_operation_id
    selected = None
    if selected_id:
        try:
            selected = manager.get_operation(selected_id)
        except CloudSyncError:
            st.session_state.syn_selected_operation_id = None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Mark Running", "mark_running", enabled=selected is not None and selected.status == SyncOperationStatus.QUEUED, disabled_reason=None if selected else "Select an operation first."),
            ToolbarAction("✅ Mark Completed", "mark_completed", enabled=selected is not None and selected.status == SyncOperationStatus.RUNNING, disabled_reason=None if selected else "Select an operation first."),
            ToolbarAction("❌ Cancel", "cancel", enabled=selected is not None and selected.status in (SyncOperationStatus.QUEUED, SyncOperationStatus.RUNNING), disabled_reason=None if selected else "Select an operation first."),
            ToolbarAction("🔄 Retry", "retry", enabled=selected is not None and selected.status in (SyncOperationStatus.FAILED, SyncOperationStatus.CANCELLED), disabled_reason=None if selected else "Select an operation first."),
        ]
    )

    if selected is not None:
        try:
            if toolbar_clicked.get("mark_running"):
                manager.mark_running(selected.id)
                notify("info", "Marked running.")
                st.rerun()
            if toolbar_clicked.get("mark_completed"):
                manager.mark_completed(selected.id, "Marked completed manually -- no real transfer occurred.")
                notify("info", "Marked completed.")
                st.rerun()
            if toolbar_clicked.get("cancel"):
                manager.cancel(selected.id)
                notify("warning", "Cancelled.")
                st.rerun()
            if toolbar_clicked.get("retry"):
                manager.retry(selected.id)
                notify("info", "Re-queued.")
                st.rerun()
        except CloudSyncError as exc:
            notify("error", str(exc))

    tabs = st.tabs(["Overview", "Providers", "Sync Queue", "Artifacts", "Snapshots", "Policies", "History", "Audit", "Settings", "Future Providers"])
    overview_tab, providers_tab, queue_tab, artifacts_tab, snapshots_tab, policies_tab, history_tab, audit_tab, settings_tab, future_tab = tabs

    with overview_tab:
        all_ops = manager.list_operations()
        counts: dict[str, int] = {}
        for op in all_ops:
            counts[op.status.value] = counts.get(op.status.value, 0) + 1
        cols = st.columns(6)
        for idx, status in enumerate(SyncOperationStatus):
            cols[idx % 6].metric(status.value, counts.get(status.value, 0))
        st.markdown(f"**Total Operations:** {len(all_ops)}")
        st.markdown(f"**Total Artifacts:** {len(manager.list_artifacts())}")
        st.markdown(f"**Total Snapshots:** {len(manager.list_snapshots())}")
        policy = manager.get_policy()
        st.markdown(f"**Default Conflict Resolution:** {policy.default_conflict_resolution}")

    with providers_tab:
        st.caption("Every provider below is a registered placeholder. Connecting, uploading, downloading, and syncing all raise 'not implemented' -- there is no real cloud connectivity in this build.")
        for descriptor in manager.list_providers():
            with st.container(border=True):
                st.markdown(f"**{descriptor.display_name}**")
                st.caption(descriptor.description)
                requirement = describe_credential_requirements(descriptor.provider_id)
                st.caption(f"Would eventually require: {', '.join(requirement.required_field_names) or '(none)'}")
                st.button("Connect", key=f"syn_connect_{descriptor.provider_id}", disabled=True, help="Not implemented -- Cloud Sync Foundation provides no real cloud connectivity.")

    with queue_tab:
        queued = manager.list_operations(status=SyncOperationStatus.QUEUED)
        running = manager.list_operations(status=SyncOperationStatus.RUNNING)
        st.markdown("**Queued**")
        if queued:
            st.dataframe([{"Object": o.object_label, "Kind": o.kind.value, "Created": o.created_at.isoformat(timespec="seconds")} for o in queued], use_container_width=True, hide_index=True)
        else:
            st.caption("Nothing queued.")
        st.markdown("**Running**")
        if running:
            st.dataframe([{"Object": o.object_label, "Kind": o.kind.value, "Started": o.started_at.isoformat(timespec="seconds") if o.started_at else "—"} for o in running], use_container_width=True, hide_index=True)
        else:
            st.caption("Nothing running.")

    with artifacts_tab:
        with st.form("syn_register_artifact_form"):
            artifact_kind = st.selectbox("Kind", [k.value for k in ArtifactKind], key="syn_artifact_kind")
            artifact_object_id = st.text_input("Object ID", key="syn_artifact_object_id")
            artifact_owner = st.text_input("Owner", key="syn_artifact_owner")
            if st.form_submit_button("Register Artifact") and artifact_object_id.strip():
                manager.register_artifact(ArtifactKind(artifact_kind), artifact_object_id.strip(), owner=artifact_owner.strip() or None)
                notify("info", "Artifact registered.")
                st.rerun()
        artifacts = manager.list_artifacts()
        if artifacts:
            st.dataframe(
                [{"Kind": a.kind.value, "Object ID": a.object_id, "Hash": a.content_hash[:12], "Version": a.version, "Status": a.status.value} for a in artifacts],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No artifacts registered yet.")

    with snapshots_tab:
        with st.form("syn_create_snapshot_form"):
            snapshot_kind = st.selectbox("Kind", [k.value for k in SnapshotKind], key="syn_snapshot_kind")
            snapshot_label = st.text_input("Label", key="syn_snapshot_label")
            snapshot_refs = st.text_area("Object References (one per line)", key="syn_snapshot_refs")
            if st.form_submit_button("Create Snapshot") and snapshot_label.strip():
                refs = [line.strip() for line in snapshot_refs.splitlines() if line.strip()]
                manager.create_snapshot(SnapshotKind(snapshot_kind), snapshot_label.strip(), refs)
                notify("info", "Snapshot created.")
                st.rerun()
        snapshots = manager.list_snapshots()
        if snapshots:
            st.dataframe(
                [{"Kind": s.kind.value, "Label": s.label, "Refs": len(s.object_refs), "Hash": s.content_hash[:12]} for s in snapshots],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No snapshots yet.")

    with policies_tab:
        policy = manager.get_policy()
        with st.form("syn_policy_form"):
            default_resolution = st.selectbox("Default Conflict Resolution", [p.value for p in ConflictResolutionPolicy], index=[p.value for p in ConflictResolutionPolicy].index(policy.default_conflict_resolution))
            auto_retry = st.checkbox("Auto-Retry Enabled (stored preference only -- nothing dispatches automatically)", value=policy.auto_retry_enabled)
            max_retry = st.number_input("Max Retry Count", min_value=0, value=policy.max_retry_count)
            if st.form_submit_button("Save Policy"):
                manager.update_policy(default_conflict_resolution=default_resolution, auto_retry_enabled=auto_retry, max_retry_count=int(max_retry))
                notify("info", "Policy updated.")
                st.rerun()

    with history_tab:
        if selected is None:
            st.caption("Select a sync operation in the Explorer to see its history.")
        else:
            records = manager.list_history(selected.id)
            if records:
                st.dataframe(
                    [{"Status": r.status.value, "Retry": r.retry_count, "Created": r.created_at.isoformat(timespec="seconds")} for r in records],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No history yet for this operation.")

    with audit_tab:
        events = manager.list_audit_events(selected.id if selected else None)
        if events:
            st.dataframe(
                [{"Event": e.event_type.value, "Key": e.key, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in events],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No audit events yet.")

    with settings_tab:
        st.info("Broader platform settings (General/Datasets/Workflow/Jobs/Risk/Charts/Reports/Notifications/Logging/Paths/Backup) live in Settings Center -- this tab only covers Cloud Sync's own conflict-resolution policy, found under the 'Policies' tab above, to avoid duplicating that page.")
        if st.button("Open Settings Center", key="syn_open_settings_center"):
            st.switch_page("pages/24_Settings_Center.py")

    with future_tab:
        st.caption("What each registered provider would eventually do, once a real implementation exists.")
        for descriptor in manager.list_providers():
            with st.container(border=True):
                st.markdown(f"**{descriptor.display_name}**")
                st.write(descriptor.description)

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card("General", [("Object", selected.object_label or selected.object_id), ("Kind", selected.kind.value), ("Status", selected.status.value)])
        render_info_card("Timing", [("Created", selected.created_at.strftime("%Y-%m-%d %H:%M:%S")), ("Retry Count", selected.retry_count)])
    else:
        st.caption("Select a sync operation in the Explorer to see its details.")
    render_info_card("Cloud Sync", [("Providers Registered", len(manager.list_providers())), ("Total Operations", len(manager.list_operations()))])

render_status_bar(
    module="Cloud Sync",
    execution_status="Ready" if selected is None else (selected.object_label or selected.object_id),
    **job_manager.status_counts(),
)
