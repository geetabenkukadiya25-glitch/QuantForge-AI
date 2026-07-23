"""A global command bar -- quick navigation to every dashboard page plus a
recent-strategies shortcut list. Navigation only (`st.switch_page`, a
built-in Streamlit multipage API); it never triggers an engine action
directly, so it cannot introduce new functionality. The three Job
Manager entries (Phase 18.4) are the one exception -- "Cancel Current
Job" calls `JobManager.cancel_running()` directly, since it's a
Job-Manager-level orchestration action, not an engine action.
"""

import streamlit as st

_ACTIONS: list[tuple[str, str]] = [
    ("Open Job Manager", "pages/18_Job_Manager.py"),
    ("Open Dataset Manager", "pages/19_Dataset_Manager.py"),
    ("Open Data Catalog", "pages/20_Data_Catalog.py"),
    ("Open Workflow Dashboard", "pages/21_Workflow_Dashboard.py"),
    ("Open Risk Analytics", "pages/22_Risk_Analytics.py"),
    ("Open Governance", "pages/23_Governance.py"),
    ("Open Settings Center", "pages/24_Settings_Center.py"),
    ("Open Cloud Sync", "pages/25_Cloud_Sync.py"),
    ("Open MT5 Integration", "pages/26_MT5_Integration.py"),
    ("Open Strategy", "pages/3_Strategy_Library.py"),
    ("Open Dataset", "pages/1_Historical_Data.py"),
    ("Chart Engine", "pages/2_Chart_Engine.py"),
    ("Context Viewer", "pages/4_Context_Viewer.py"),
    ("Indicator Explorer", "pages/5_Indicator_Explorer.py"),
    ("Smart Money Explorer", "pages/6_Smart_Money_Explorer.py"),
    ("Strategy Builder", "pages/7_Strategy_Builder_Explorer.py"),
    ("Run Backtest", "pages/8_Backtesting_Dashboard.py"),
    ("Optimization", "pages/9_Optimization_Dashboard.py"),
    ("Validation", "pages/10_Validation_Dashboard.py"),
    ("Replay", "pages/11_Replay_Dashboard.py"),
    ("Research", "pages/12_Research_Dashboard.py"),
    ("Knowledge Base", "pages/13_Knowledge_Base.py"),
    ("Extraction", "pages/14_Extraction_Dashboard.py"),
    ("Portfolio", "pages/15_Portfolio_Dashboard.py"),
    ("AI Assistant", "pages/16_AI_Assistant.py"),
    ("EA Generator", "pages/17_EA_Generator.py"),
    ("Settings", "dashboard.py"),
    ("Documentation", "dashboard.py"),
]


def render_command_bar(current_page: str) -> None:
    with st.popover("⌘ Command Bar"):
        query = st.text_input("Search", key="qf_command_bar_query", placeholder="Jump to a dashboard...")
        matches = [a for a in _ACTIONS if query.lower() in a[0].lower()] if query else _ACTIONS
        for label, target in matches:
            if st.button(label, key=f"cmdbar_{current_page}_{label}", use_container_width=True):
                st.switch_page(target)

        if st.button("Open History", key=f"cmdbar_{current_page}_open_history", use_container_width=True):
            st.session_state.jm_default_tab = "History"
            st.switch_page("pages/18_Job_Manager.py")

        if st.button("Cancel Current Job", key=f"cmdbar_{current_page}_cancel_current_job", use_container_width=True):
            from app.job_manager import get_job_manager

            cancelled = get_job_manager().cancel_running()
            if cancelled is not None:
                st.toast(f"Cancel requested for '{cancelled.name}'.")
            else:
                st.toast("No job is currently running.")

        from app.job_manager import get_job_manager
        from app.job_manager.job_state import JobState

        retriable = [j for j in get_job_manager().list() if j.state != JobState.QUEUED and j.state != JobState.RUNNING]
        if st.button(
            "Retry Last Job",
            key=f"cmdbar_{current_page}_retry_last_job",
            use_container_width=True,
            disabled=not retriable,
            help="Re-submit the most recent finished job." if retriable else "No finished job to retry yet.",
        ):
            retried = get_job_manager().retry(retriable[0].id)
            st.toast(f"Retried '{retried.name}'.")
            st.rerun()

        show_progress = st.session_state.get("qf_show_runtime_monitor", True)
        if show_progress:
            if st.button("Hide Progress", key=f"cmdbar_{current_page}_hide_progress", use_container_width=True):
                st.session_state.qf_show_runtime_monitor = False
                st.rerun()
        else:
            if st.button("Show Progress", key=f"cmdbar_{current_page}_show_progress", use_container_width=True):
                st.session_state.qf_show_runtime_monitor = True
                st.rerun()

        try:
            from app.strategy_library import StrategyLibraryManager

            recent = StrategyLibraryManager().list_recent()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent = []
        if recent:
            st.divider()
            st.caption("Recent Files")
            for path in recent[:5]:
                st.caption(path.name)

        try:
            from app.dataset_manager import DatasetManager

            recent_datasets = DatasetManager().list_recent()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_datasets = []
        if recent_datasets:
            st.divider()
            st.caption("Recent Datasets")
            for record in recent_datasets[:5]:
                st.caption(record.display_name)

        try:
            from app.data_catalog import DataCatalog

            recently_used = sorted(
                (e for e in DataCatalog().list_catalog(archived=None) if e.last_used is not None),
                key=lambda e: e.last_used,
                reverse=True,
            )
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recently_used = []
        if recently_used:
            st.divider()
            st.caption("Recently Used")
            for entry in recently_used[:5]:
                st.caption(entry.display_name)

        try:
            from app.workflow import WorkflowManager

            recent_workflows = sorted(
                (w for w in WorkflowManager().list_entries(archived=None)),
                key=lambda w: w.updated_at,
                reverse=True,
            )
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_workflows = []
        if recent_workflows:
            st.divider()
            st.caption("Recent Workflows")
            for workflow in recent_workflows[:5]:
                st.caption(workflow.name)

        try:
            from app.risk_analytics import get_risk_manager

            recent_reports = get_risk_manager().list_reports()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_reports = []
        if recent_reports:
            st.divider()
            st.caption("Recent Risk Reports")
            for report in recent_reports[:5]:
                st.caption(report.title)

        try:
            from app.governance import get_governance_manager

            recent_governance = get_governance_manager().list_entries()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_governance = []
        if recent_governance:
            st.divider()
            st.caption("Recent Governance Records")
            for record in recent_governance[:5]:
                st.caption(f"{record.object_label or record.object_id} ({record.status.value})")

        try:
            from app.cloud_sync import get_sync_manager

            recent_sync_ops = get_sync_manager().list_operations()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_sync_ops = []
        if recent_sync_ops:
            st.divider()
            st.caption("Recent Cloud Sync Operations")
            for operation in recent_sync_ops[:5]:
                st.caption(f"{operation.object_label or operation.object_id} ({operation.status.value})")

        try:
            from app.mt5 import get_mt5_manager

            recent_mt5_events = get_mt5_manager().list_audit_events()
        except Exception:  # noqa: BLE001 -- command bar must never crash a page over an optional recents list
            recent_mt5_events = []
        if recent_mt5_events:
            st.divider()
            st.caption("Recent MT5 Connection Events")
            for event in recent_mt5_events[:5]:
                st.caption(f"{event.event_type.value} ({event.key})")
