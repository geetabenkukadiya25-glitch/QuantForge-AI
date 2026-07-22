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
