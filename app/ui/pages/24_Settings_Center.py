"""
Streamlit page: Settings Center.

The central UI for the Institutional Settings Center (Phase 18.8) --
General/Datasets/Workflow/Jobs/Risk/Charts/Reports/Notifications/
Logging/Paths/Backup/About, all backed by one persisted `SettingsState`
document. This page never modifies any engine, Job Manager, Dataset
Manager, Data Catalog, Workflow, Risk Analytics, Governance, Strategy
Library, or SDL module -- it is the canonical settings *store*, not yet
wired into any other module's runtime behavior (see the page's own
Paths-tab copy and the phase's Known Limitations).

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `set_*` session-state prefix. Settings is a
singleton document (not a collection), so the Explorer shows Quick
Actions + recent audit events instead of an entity list.
"""

import platform
import subprocess

import streamlit as st

from app.job_manager import JobState, get_job_manager
from app.settings_center import get_settings_center_manager
from app.settings_center.exceptions import SettingsError
from app.settings_center.paths import list_managed_folders, open_folder
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

st.set_page_config(page_title="Settings Center - QuantForge AI", page_icon="⚙", layout="wide")


@st.cache_data(show_spinner=False)
def _about_info() -> dict:
    """Computed once per process (not once per script rerun) -- the git
    subprocess call and package-version lookups are read-only and don't
    change within a session, so there's no reason to redo them on every
    Streamlit rerun."""
    try:
        git_rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        git_rev = None

    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as pkg_version

    packages = []
    for pkg in ("streamlit", "pandas", "numpy", "pydantic", "plotly"):
        try:
            packages.append({"Package": pkg, "Version": pkg_version(pkg)})
        except PackageNotFoundError:
            packages.append({"Package": pkg, "Version": "not installed"})

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_revision": git_rev or "unavailable",
        "packages": packages,
    }

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Settings Center")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Settings Center")
st.caption(
    "Institutional Settings Center -- the canonical, persisted store for platform-wide configuration. This phase "
    "does not rewire any other module to read from here yet; every value below is stored and displayed, not "
    "enforced (see the Paths tab and Known Limitations)."
)

manager = get_settings_center_manager()
job_manager = get_job_manager()

st.session_state.setdefault("set_current_job_id", None)
st.session_state.setdefault("set_last_export", None)
st.session_state.setdefault("set_reset_all_armed", False)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    st.markdown("**Quick Actions**")
    if st.button("📤 Export Settings", key="set_quick_export", use_container_width=True):
        job = manager.submit_export()
        st.session_state.set_current_job_id = job.id
        notify("info", f"Queued: {job.name}")
        st.rerun()
    if st.button("💾 Backup Now", key="set_quick_backup", use_container_width=True):
        job = manager.submit_backup()
        st.session_state.set_current_job_id = job.id
        notify("info", f"Queued: {job.name}")
        st.rerun()
    if st.button("♻ Reset All to Defaults", key="set_quick_reset_all", use_container_width=True):
        st.session_state.set_reset_all_armed = True

    if st.session_state.set_reset_all_armed:
        st.warning("Reset EVERY settings section to its default value? This cannot be undone.")
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Reset", type="primary", key="set_confirm_reset_all"):
            manager.reset_all_to_defaults()
            st.session_state.set_reset_all_armed = False
            notify("warning", "All settings reset to defaults.")
            st.rerun()
        if confirm_cols[1].button("Cancel", key="set_cancel_reset_all"):
            st.session_state.set_reset_all_armed = False
            st.rerun()

    current_job = job_manager.get(st.session_state.set_current_job_id) if st.session_state.set_current_job_id else None
    if current_job is not None and current_job.state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
        render_runtime_monitor(current_job.id)
    elif current_job is not None and current_job.state == JobState.COMPLETED:
        if current_job.name == "Export Settings":
            st.session_state.set_last_export = current_job.result
        st.session_state.set_current_job_id = None
        st.rerun()
    elif current_job is not None and current_job.state == JobState.FAILED:
        st.error(f"Action failed: {current_job.error}")

    st.divider()
    st.markdown("**Recent Audit Events**")
    events = manager.list_audit_events(limit=10)
    if not events:
        st.caption("No audit events yet.")
    else:
        for event in events:
            st.caption(f"{event.event_type.value} · {event.key} · {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

with workspace_col:
    state = manager.get_state()

    tabs = st.tabs(["General", "Datasets", "Workflow", "Jobs", "Risk", "Charts", "Reports", "Notifications", "Logging", "Paths", "Backup", "About"])
    general_tab, datasets_tab, workflow_tab, jobs_tab, risk_tab, charts_tab, reports_tab, notif_tab, logging_tab, paths_tab, backup_tab, about_tab = tabs

    def _save_section(section_name: str, **fields) -> None:
        try:
            manager.update_section(section_name, **fields)
        except SettingsError as exc:
            notify("error", str(exc))
        else:
            notify("info", f"Saved {section_name} settings.")
            st.rerun()

    with general_tab:
        with st.form("set_general_form"):
            project_name = st.text_input("Project Name", value=state.general.project_name)
            organization = st.text_input("Organization", value=state.general.organization)
            author = st.text_input("Author", value=state.general.author)
            timezone = st.text_input("Timezone", value=state.general.timezone)
            language = st.selectbox("Language", ["en"], index=0, help="No i18n system exists yet -- English only.")
            theme = st.selectbox("Theme", ["dark", "light", "auto"], index=["dark", "light", "auto"].index(state.general.theme))
            if st.form_submit_button("Save"):
                _save_section("general", project_name=project_name, organization=organization, author=author, timezone=timezone, language=language, theme=theme)

    with datasets_tab:
        with st.form("set_datasets_form"):
            st.text_input("Registry Path", value=state.datasets.registry_path_display, disabled=True)
            st.text_input("Import Path", value=state.datasets.import_path_display, disabled=True)
            cache_enabled = st.checkbox("Cache Enabled", value=state.datasets.cache_enabled)
            cleanup_max_versions = st.number_input("Cleanup: Max Versions Kept", min_value=1, value=state.datasets.cleanup_max_versions)
            preview_rows = st.number_input("Preview Size (rows)", min_value=1, value=state.datasets.preview_rows)
            if st.form_submit_button("Save"):
                _save_section("datasets", cache_enabled=cache_enabled, cleanup_max_versions=int(cleanup_max_versions), preview_rows=int(preview_rows))

    with workflow_tab:
        st.caption("Stored preferences only -- not yet wired into the Workflow Engine's per-step defaults.")
        with st.form("set_workflow_form"):
            retry_count = st.number_input("Retry Count", min_value=0, value=state.workflow.retry_count)
            timeout_seconds = st.number_input("Timeout (seconds, 0 = disabled)", min_value=0.0, value=state.workflow.timeout_seconds)
            parallel_jobs = st.number_input("Parallel Jobs", min_value=1, value=state.workflow.parallel_jobs)
            queue_size = st.number_input("Queue Size (0 = unbounded)", min_value=0, value=state.workflow.queue_size)
            if st.form_submit_button("Save"):
                _save_section("workflow", retry_count=int(retry_count), timeout_seconds=float(timeout_seconds), parallel_jobs=int(parallel_jobs), queue_size=int(queue_size))

    with jobs_tab:
        st.caption("Stored preferences only -- not yet wired into Job Manager's real retention/refresh behavior.")
        with st.form("set_jobs_form"):
            history_retention = st.number_input("History Retention (records)", min_value=1, value=state.jobs.history_retention)
            refresh_interval = st.number_input("Refresh Interval (seconds)", min_value=0.1, value=state.jobs.refresh_interval_seconds)
            progress_frequency = st.number_input("Progress Update Frequency (seconds)", min_value=0.1, value=state.jobs.progress_update_frequency)
            cleanup_policy = st.selectbox("Cleanup Policy", ["keep_last_n", "time_based", "manual"], index=["keep_last_n", "time_based", "manual"].index(state.jobs.cleanup_policy))
            if st.form_submit_button("Save"):
                _save_section("jobs", history_retention=int(history_retention), refresh_interval_seconds=float(refresh_interval), progress_update_frequency=float(progress_frequency), cleanup_policy=cleanup_policy)

    with risk_tab:
        st.caption("Stored preferences only -- not yet wired into Risk Analytics' actual analysis defaults.")
        with st.form("set_risk_form"):
            default_confidence = st.slider("Default Confidence", 0.5, 0.999, value=state.risk.default_confidence)
            var_pct = st.slider("VaR %", 0.5, 0.999, value=state.risk.var_pct)
            cvar_pct = st.slider("CVaR %", 0.5, 0.999, value=state.risk.cvar_pct)
            monte_carlo_iterations = st.number_input("Monte Carlo Iterations", min_value=1, value=state.risk.monte_carlo_iterations)
            scenario_defaults = st.multiselect("Scenario Defaults", ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "LOW_VOLATILITY"], default=state.risk.scenario_defaults)
            if st.form_submit_button("Save"):
                _save_section("risk", default_confidence=default_confidence, var_pct=var_pct, cvar_pct=cvar_pct, monte_carlo_iterations=int(monte_carlo_iterations), scenario_defaults=scenario_defaults)

    with charts_tab:
        st.caption("Theme/candle colors reuse the real Chart Engine theme system.")
        with st.form("set_charts_form"):
            chart_theme = st.selectbox("Theme", ["dark", "light"], index=["dark", "light"].index(state.charts.theme))
            show_grid = st.checkbox("Show Grid", value=state.charts.show_grid)
            font_family = st.text_input("Font Family", value=state.charts.font_family)
            candle_up = st.color_picker("Candle Up Color", value=state.charts.candle_up_color)
            candle_down = st.color_picker("Candle Down Color", value=state.charts.candle_down_color)
            export_dpi = st.number_input("Export DPI", min_value=1, value=state.charts.export_dpi)
            default_width = st.number_input("Default Width", min_value=1, value=state.charts.default_width)
            default_height = st.number_input("Default Height", min_value=1, value=state.charts.default_height)
            if st.form_submit_button("Save"):
                _save_section("charts", theme=chart_theme, show_grid=show_grid, font_family=font_family, candle_up_color=candle_up, candle_down_color=candle_down, export_dpi=int(export_dpi), default_width=int(default_width), default_height=int(default_height))

    with reports_tab:
        st.caption("Excel/PDF export are not implemented anywhere in this project yet -- those toggles are locked off.")
        with st.form("set_reports_form"):
            html_enabled = st.checkbox("HTML Reports Enabled", value=state.reports.html_enabled)
            st.checkbox("Excel Reports Enabled", value=False, disabled=True, help="No Excel export capability exists yet.")
            st.checkbox("PDF Reports Enabled", value=False, disabled=True, help="No PDF export capability exists yet.")
            branding_name = st.text_input("Branding Name", value=state.reports.branding_name)
            logo_path = st.text_input("Logo Path", value=state.reports.logo_path)
            footer_text = st.text_input("Footer Text", value=state.reports.footer_text)
            if st.form_submit_button("Save"):
                _save_section("reports", html_enabled=html_enabled, excel_enabled=False, pdf_enabled=False, branding_name=branding_name, logo_path=logo_path, footer_text=footer_text)

    with notif_tab:
        st.caption("Desktop notifications/sounds are not implemented anywhere in this project yet -- those toggles are locked off.")
        with st.form("set_notifications_form"):
            toast_enabled = st.checkbox("Toast Notifications Enabled", value=state.notifications.toast_enabled)
            st.checkbox("Desktop Notifications Enabled", value=False, disabled=True, help="No desktop-notification integration exists yet.")
            st.checkbox("Sounds Enabled", value=False, disabled=True, help="No sound integration exists yet.")
            notify_job_completion = st.checkbox("Notify on Job Completion", value=state.notifications.notify_on_job_completion)
            notify_errors = st.checkbox("Notify on Errors", value=state.notifications.notify_on_errors)
            if st.form_submit_button("Save"):
                _save_section("notifications", toast_enabled=toast_enabled, desktop_enabled=False, sounds_enabled=False, notify_on_job_completion=notify_job_completion, notify_on_errors=notify_errors)

    with logging_tab:
        with st.form("set_logging_form"):
            log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(state.logging.log_level))
            audit_retention_days = st.number_input("Audit Retention (days)", min_value=1, value=state.logging.audit_retention_days)
            runtime_retention_days = st.number_input("Runtime Retention (days)", min_value=1, value=state.logging.runtime_retention_days)
            cleanup_enabled = st.checkbox("Cleanup Enabled", value=state.logging.cleanup_enabled)
            if st.form_submit_button("Save"):
                _save_section("logging", log_level=log_level, audit_retention_days=int(audit_retention_days), runtime_retention_days=int(runtime_retention_days), cleanup_enabled=cleanup_enabled)

    with paths_tab:
        st.caption("Change/Reset Folder only store an override here -- they do not yet redirect any other module's actual file I/O (see Known Limitations).")
        for folder in list_managed_folders():
            with st.container(border=True):
                override = state.path_overrides.get(folder["key"])
                st.markdown(f"**{folder['key']}**")
                st.caption(override or folder["path"])
                cols = st.columns(3)
                if cols[0].button("Open Folder", key=f"set_open_{folder['key']}"):
                    if open_folder(override or folder["path"]):
                        notify("info", f"Opened '{folder['key']}'.")
                    else:
                        notify("error", f"Could not open '{folder['key']}'.")
                new_path = cols[1].text_input("New path", key=f"set_change_input_{folder['key']}", label_visibility="collapsed", placeholder="Change folder...")
                if cols[1].button("Change Folder", key=f"set_change_{folder['key']}", disabled=not new_path.strip()):
                    manager.set_path_override(folder["key"], new_path.strip())
                    notify("info", f"Override stored for '{folder['key']}'.")
                    st.rerun()
                if cols[2].button("Reset Folder", key=f"set_reset_{folder['key']}", disabled=override is None):
                    manager.reset_path_override(folder["key"])
                    notify("info", f"Override cleared for '{folder['key']}'.")
                    st.rerun()

    with backup_tab:
        st.markdown("**Export**")
        if st.session_state.set_last_export is not None:
            st.download_button("Download settings.json", data=st.session_state.set_last_export, file_name="settings.json", mime="application/json")
        else:
            st.caption("Click 'Export Settings' in the Explorer to prepare a download.")

        st.markdown("**Import**")
        uploaded = st.file_uploader("Upload a settings.json file", type=["json"], key="set_import_uploader")
        if uploaded is not None and st.button("Import", key="set_import_button"):
            try:
                manager.import_now(uploaded.getvalue())
            except SettingsError as exc:
                notify("error", f"Import failed: {exc}")
            else:
                notify("info", "Settings imported.")
                st.rerun()

        st.markdown("**Backups**")
        backups = manager.list_backups()
        if not backups:
            st.caption("No backups yet -- click 'Backup Now' in the Explorer.")
        else:
            for backup in backups:
                with st.container(border=True):
                    st.markdown(f"**{backup['name']}**")
                    st.caption(backup["modified"])
                    if st.button("Restore", key=f"set_restore_{backup['name']}"):
                        try:
                            manager.restore_now(backup["name"])
                        except SettingsError as exc:
                            notify("error", f"Restore failed: {exc}")
                        else:
                            notify("info", f"Restored '{backup['name']}'.")
                            st.rerun()

    with about_tab:
        about = _about_info()
        st.markdown("**Version:** 0.1.0-dev *(no authoritative version file exists in this repo yet -- placeholder)*")
        st.markdown(f"**Python Version:** {about['python_version']}")
        st.markdown(f"**Platform:** {about['platform']}")
        st.markdown(f"**Git Revision:** {about['git_revision']}")
        st.markdown("**Installed Modules (key packages):**")
        st.dataframe(about["packages"], use_container_width=True, hide_index=True)

with info_col:
    st.subheader("Information")
    render_info_card("General", [("Project", state.general.project_name), ("Theme", state.general.theme), ("Version", state.version)])
    render_info_card("Updated", [("Last Updated", state.updated_at.strftime("%Y-%m-%d %H:%M:%S"))])
    render_info_card("Audit", [("Total events", len(manager.list_audit_events()))])
    render_info_card("Backups", [("Total backups", len(manager.list_backups()))])

render_status_bar(module="Settings Center", execution_status="Ready", **job_manager.status_counts())
