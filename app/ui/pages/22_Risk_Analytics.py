"""
Streamlit page: Risk Analytics.

The central UI for Institutional Risk Analytics (Phase 17.7) -- read-only
analysis of already-completed Backtest results: drawdown, VaR/CVaR,
Monte Carlo tail-risk, scenario analysis, correlation, and time-bucketed
heatmaps. This page never re-executes a strategy and never influences
trading; every long analysis runs as an ordinary Job Manager job.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page (Workflow Dashboard, Data Catalog), `ra_*`
session-state prefix.
"""

import streamlit as st

from app.dataset_manager import DatasetManager
from app.job_manager import JobState, get_job_manager
from app.risk_analytics import RiskReportKind, get_risk_manager
from app.risk_analytics.exceptions import RiskAnalyticsError
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

st.set_page_config(page_title="Risk Analytics - QuantForge AI", page_icon="📉", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Risk Analytics")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Risk Analytics")
st.caption(
    "Institutional risk analysis over already-completed backtests -- drawdown, VaR/CVaR, Monte Carlo, "
    "scenario analysis, correlation, and heatmaps. Read-only: this page never re-executes a strategy."
)

manager = get_risk_manager()
job_manager = get_job_manager()
dataset_manager = DatasetManager()

st.session_state.setdefault("ra_selected_id", None)
st.session_state.setdefault("ra_delete_armed", False)
st.session_state.setdefault("ra_current_job_id", None)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    with st.expander("▶ New Analysis"):
        source_job_id = st.text_input("Source Job ID (a completed Backtest job)", key="ra_source_job_id")
        source_label = st.text_input("Label", value="Backtest Analysis", key="ra_source_label")
        dataset_options = {"(none)": None}
        for record in dataset_manager.list_entries(archived=False):
            dataset_options[record.display_name] = record.id
        dataset_choice = st.selectbox("Dataset (for scenario analysis)", list(dataset_options.keys()), key="ra_dataset_choice")
        if st.button("Run Analysis", key="ra_run_analysis"):
            dataset_df = None
            dataset_id = dataset_options[dataset_choice]
            if dataset_id is not None:
                dataset_df = dataset_manager.load_dataframe(dataset_id)
            try:
                job = manager.submit_analysis(source_job_id, source_label, dataset_df=dataset_df)
            except RiskAnalyticsError as exc:
                notify("error", f"Cannot run analysis: {exc}")
            else:
                st.session_state.ra_current_job_id = job.id
                notify("info", f"Queued: {job.name}")
                st.rerun()

    current_job = job_manager.get(st.session_state.ra_current_job_id) if st.session_state.ra_current_job_id else None
    if current_job is not None and current_job.state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
        render_runtime_monitor(current_job.id)
    elif current_job is not None and current_job.state == JobState.COMPLETED:
        st.session_state.ra_selected_id = current_job.result.id
        st.session_state.ra_current_job_id = None
        st.rerun()
    elif current_job is not None and current_job.state == JobState.FAILED:
        st.error(f"Analysis failed: {current_job.error}")

    st.markdown("**Saved Reports**")
    reports = manager.list_reports()
    if not reports:
        st.caption("No risk reports yet -- run an analysis above.")
    for report in reports:
        with st.container(border=True):
            is_selected = st.session_state.ra_selected_id == report.id
            st.markdown(f"{'▶ ' if is_selected else ''}**{report.title}**")
            st.caption(f"{report.kind.value} · {report.source_description}")
            if st.button("Select", key=f"ra_select_{report.id}", use_container_width=True, disabled=is_selected):
                st.session_state.ra_selected_id = report.id
                st.rerun()

with workspace_col:
    selected_id = st.session_state.ra_selected_id
    selected = manager.get_report(selected_id) if selected_id else None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("📤 Export HTML", "export", enabled=selected is not None, disabled_reason=None if selected else "Select a report first."),
            ToolbarAction("🗑 Delete", "delete", enabled=selected is not None, disabled_reason=None if selected else "Select a report first."),
        ]
    )

    if selected is not None and toolbar_clicked.get("delete"):
        st.session_state.ra_delete_armed = True

    if st.session_state.ra_delete_armed and selected is not None:
        st.warning(f"Delete '{selected.title}'? This cannot be undone.")
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Delete", type="primary"):
            manager.delete_report(selected.id)
            st.session_state.ra_selected_id = None
            st.session_state.ra_delete_armed = False
            notify("warning", f"Deleted '{selected.title}'.")
            st.rerun()
        if confirm_cols[1].button("Cancel"):
            st.session_state.ra_delete_armed = False
            st.rerun()

    if selected is None:
        st.info("Select a saved risk report in the Explorer, or run a new analysis.")
        render_status_bar(module="Risk Analytics", execution_status="Ready", **job_manager.status_counts())
        st.stop()

    if toolbar_clicked.get("export"):
        from app.risk_analytics.risk_reports import export_html

        payload = export_html(selected)
        st.download_button("Download HTML report", data=payload, file_name=f"{selected.title.replace(' ', '_')}.html", mime="text/html")

    sections = selected.sections
    tabs = st.tabs(["Overview", "Portfolio", "Exposure", "Drawdown", "VaR", "CVaR", "Monte Carlo", "Heatmaps", "Correlation", "Reports", "Audit"])
    overview_tab, portfolio_tab, exposure_tab, drawdown_tab, var_tab, cvar_tab, monte_carlo_tab, heatmaps_tab, correlation_tab, reports_tab, audit_tab = tabs

    with overview_tab:
        overview = sections.get("overview")
        if not overview:
            st.caption("No overview data in this report.")
        else:
            perf = overview.get("performance", {})
            cols = st.columns(4)
            cols[0].metric("Total Trades", perf.get("total_trades", "—"))
            cols[1].metric("Win Rate", f"{perf.get('win_rate', 0) * 100:.1f}%")
            cols[2].metric("Net Profit", f"{perf.get('net_profit', 0):,.2f}")
            cols[3].metric("Profit Factor", f"{perf.get('profit_factor', 0):.2f}" if perf.get("profit_factor") is not None else "—")
            cols2 = st.columns(4)
            cols2[0].metric("Sharpe", f"{perf.get('sharpe_ratio', 0):.2f}" if perf.get("sharpe_ratio") is not None else "—")
            cols2[1].metric("Sortino", f"{perf.get('sortino_ratio', 0):.2f}" if perf.get("sortino_ratio") is not None else "—")
            cols2[2].metric("Calmar", f"{perf.get('calmar_ratio', 0):.2f}" if perf.get("calmar_ratio") is not None else "—")
            cols2[3].metric("Expectancy", f"{perf.get('expectancy', 0):,.4f}")
            st.markdown("**Risk Metrics**")
            st.json(overview.get("risk_metrics", {}))
            st.markdown("**Consecutive Streaks**")
            st.json(overview.get("consecutive_streaks", {}))

    with portfolio_tab:
        portfolio_risk = sections.get("portfolio_risk")
        if not portfolio_risk:
            st.caption("No portfolio-level risk data in this report (single-strategy analysis).")
        else:
            st.json(portfolio_risk)

    with exposure_tab:
        exposure = sections.get("exposure")
        if not exposure:
            st.caption("No exposure data in this report.")
        else:
            st.json(exposure)

    with drawdown_tab:
        drawdown = sections.get("overview", {}).get("drawdown")
        if not drawdown:
            st.caption("No drawdown data in this report.")
        else:
            cols = st.columns(3)
            cols[0].metric("Max Drawdown", f"{drawdown.get('max_drawdown', 0):,.2f}")
            cols[1].metric("Max Drawdown %", f"{drawdown.get('max_drawdown_pct', 0):.2f}%")
            cols[2].metric("Avg Recovery (bars)", drawdown.get("average_recovery_time_bars") or "—")
            st.markdown("**Episodes**")
            episodes = drawdown.get("episodes", [])
            st.dataframe(episodes, use_container_width=True, hide_index=True) if episodes else st.caption("No drawdown episodes.")

    with var_tab:
        var_rows = sections.get("var", [])
        if not var_rows:
            st.caption("No VaR data in this report.")
        else:
            st.dataframe(var_rows, use_container_width=True, hide_index=True)

    with cvar_tab:
        cvar_rows = sections.get("cvar", [])
        if not cvar_rows:
            st.caption("No CVaR data in this report.")
        else:
            st.dataframe(cvar_rows, use_container_width=True, hide_index=True)

    with monte_carlo_tab:
        mc = sections.get("monte_carlo")
        if not mc:
            st.caption("No Monte Carlo data in this report.")
        else:
            cols = st.columns(4)
            cols[0].metric("Iterations", mc.get("iterations_run", "—"))
            cols[1].metric("Mean Net Profit", f"{mc.get('mean_net_profit', 0):,.2f}")
            cols[2].metric("Probability of Profit", f"{mc.get('probability_of_profit', 0) * 100:.1f}%")
            cols[3].metric("Probability of Ruin", f"{mc.get('probability_of_ruin', 0) * 100:.1f}%")
            st.json(mc)

    with heatmaps_tab:
        heatmaps = sections.get("heatmaps", {})
        if not heatmaps:
            st.caption("No heatmap data in this report.")
        else:
            heatmap_choice = st.selectbox("Heatmap", list(heatmaps.keys()), key="ra_heatmap_choice")
            buckets = heatmaps[heatmap_choice].get("buckets", {})
            st.bar_chart(buckets) if buckets else st.caption("No data for this bucket.")

    with correlation_tab:
        correlation = sections.get("correlation")
        if not correlation:
            st.caption("No correlation data in this report.")
        else:
            st.metric("Average Correlation", f"{correlation.get('average_correlation', 0):.4f}")
            st.dataframe(correlation.get("pairs", []), use_container_width=True, hide_index=True)

    with reports_tab:
        st.markdown(f"**Kind:** {selected.kind.value}")
        st.markdown(f"**Source:** {selected.source_description}")
        st.markdown(f"**Created:** {selected.created_at.isoformat(timespec='seconds')}")
        st.markdown("**Scenarios**")
        scenarios = sections.get("scenarios", [])
        st.dataframe(scenarios, use_container_width=True, hide_index=True) if scenarios else st.caption("No scenario data.")

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

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card("General", [("Title", selected.title), ("Kind", selected.kind.value), ("Created", selected.created_at.strftime("%Y-%m-%d %H:%M"))])
        render_info_card("Source", [("Description", selected.source_description)])
        overview = sections.get("overview", {}).get("performance", {})
        render_info_card(
            "Key Metrics",
            [
                ("Net Profit", f"{overview.get('net_profit', 0):,.2f}"),
                ("Win Rate", f"{overview.get('win_rate', 0) * 100:.1f}%"),
                ("Sharpe", f"{overview.get('sharpe_ratio', 0):.2f}" if overview.get("sharpe_ratio") is not None else "—"),
            ],
        )
        render_info_card("Audit", [("Total events", len(manager.list_audit_events(selected.id)))])
    else:
        st.caption("Select a risk report in the Explorer to see its details.")

render_status_bar(
    module="Risk Analytics",
    execution_status="Ready" if selected is None else selected.title,
    **job_manager.status_counts(),
)
