"""
Streamlit page: MT5 Data Synchronization.

The central UI for the Institutional MT5 Live Data Synchronization
Engine (Phase 19.2) -- READ-ONLY. Synchronizes symbols, ticks, bars,
Market Watch quotes, Market Book depth, spreads, and session windows by
calling `MT5Manager`'s and `BridgeExchangeManager`'s existing public
methods only. No order execution, no trade instruction, no broker
control anywhere on this page. Any JSON export goes through the
existing JSON Bridge (`SyncEngineManager.export_via_bridge`), never a
second JSON path.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `mts_*` session-state prefix.
"""

import streamlit as st

from app.job_manager import get_job_manager
from app.mt5 import ConnectionState, get_mt5_manager
from app.mt5.exceptions import MT5Error
from app.mt5_sync import SyncKind, get_sync_engine_manager
from app.ui.components import notify, render_command_bar, render_info_card, render_notification_center, render_shell, render_status_bar

st.set_page_config(page_title="MT5 Data Sync - QuantForge AI", page_icon="🔄", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("MT5 Data Synchronization")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("MT5 Data Synchronization")
st.caption(
    "Read-only live data synchronization. Every sync call maps to an existing MT5Manager read-only method -- "
    "no order execution, no trade instruction, no broker control anywhere on this page."
)

mt5_manager = get_mt5_manager()
sync_manager = get_sync_engine_manager()
job_manager = get_job_manager()

st.session_state.setdefault("mts_selected_symbol", "EURUSD")

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    with st.container(border=True):
        st.markdown(f"**Connection:** {mt5_manager.connection_state.value}")
        health = sync_manager.get_health()
        st.markdown(f"**Sync Health:** {health.overall_status}")

    symbol_options = []
    if mt5_manager.connection_state == ConnectionState.CONNECTED:
        try:
            symbol_options = [s.name for s in mt5_manager.list_symbols() if s.visible]
        except MT5Error:
            symbol_options = []
    if symbol_options:
        default_index = symbol_options.index(st.session_state.mts_selected_symbol) if st.session_state.mts_selected_symbol in symbol_options else 0
        st.session_state.mts_selected_symbol = st.selectbox("Symbol", symbol_options, index=default_index, key="mts_symbol_select")
    else:
        st.text_input("Symbol (manual)", key="mts_selected_symbol")

    st.markdown("**Recent Sync Activity**")
    events = sync_manager.list_audit_events(limit=10)
    if not events:
        st.caption("No sync activity yet -- run a sync from a tab.")
    for event in events:
        st.caption(f"{event.event_type.value} — {event.timestamp.strftime('%H:%M:%S')}")

with workspace_col:
    tabs = st.tabs(["Overview", "Tick Sync", "Bar Sync", "Market Watch", "Spread", "Market Book", "Sessions", "Statistics", "Diagnostics", "Audit", "Health"])
    (
        overview_tab, tick_tab, bar_tab, watch_tab, spread_tab,
        book_tab, sessions_tab, stats_tab, diagnostics_tab, audit_tab, health_tab,
    ) = tabs

    symbol = st.session_state.mts_selected_symbol

    with overview_tab:
        stats = sync_manager.get_statistics()
        cols = st.columns(4)
        cols[0].metric("Total Runs", stats.total_runs)
        cols[1].metric("Success", stats.success_count)
        cols[2].metric("Failures", stats.failure_count)
        cols[3].metric("Avg Latency (ms)", f"{stats.average_latency_ms:.2f}")
        if st.button("Sync Symbols", key="mts_sync_symbols"):
            run = sync_manager.sync_symbols()
            notify("info" if run.status.value == "COMPLETED" else "error", f"Symbol sync: {run.status.value} ({run.records_synced} synced).")
            st.rerun()

    with tick_tab:
        count = st.number_input("Tick Count", min_value=1, value=50, key="mts_tick_count")
        if st.button("Sync Ticks", key="mts_sync_ticks", disabled=not symbol):
            run = sync_manager.sync_ticks(symbol, int(count))
            st.session_state.mts_last_tick_run = run
            notify("info" if run.status.value == "COMPLETED" else "error", f"Tick sync: {run.status.value}.")
            st.rerun()
        if st.session_state.get("mts_last_tick_run"):
            run = st.session_state.mts_last_tick_run
            st.json(run.to_dict())

    with bar_tab:
        timeframe = st.text_input("Timeframe", value="H1", key="mts_bar_timeframe")
        bar_count = st.number_input("Bar Count", min_value=1, value=50, key="mts_bar_count")
        if st.button("Sync Bars", key="mts_sync_bars", disabled=not symbol):
            run = sync_manager.sync_bars(symbol, timeframe.strip() or "H1", int(bar_count))
            st.session_state.mts_last_bar_run = run
            notify("info" if run.status.value == "COMPLETED" else "error", f"Bar sync: {run.status.value}.")
            st.rerun()
        if st.session_state.get("mts_last_bar_run"):
            st.json(st.session_state.mts_last_bar_run.to_dict())

    with watch_tab:
        watch_symbols_raw = st.text_area("Symbols (one per line)", value=symbol, key="mts_watch_symbols")
        if st.button("Sync Market Watch", key="mts_sync_watch"):
            symbols_list = [s.strip() for s in watch_symbols_raw.splitlines() if s.strip()]
            try:
                run = sync_manager.sync_market_watch(symbols_list)
                st.session_state.mts_last_watch_run = run
                notify("info" if run.status.value == "COMPLETED" else "error", f"Market Watch sync: {run.status.value}.")
            except MT5Error as exc:
                notify("error", str(exc))
            st.rerun()
        if st.session_state.get("mts_last_watch_run"):
            st.json(st.session_state.mts_last_watch_run.to_dict())

    with spread_tab:
        if st.button("Sample Spread", key="mts_sample_spread", disabled=not symbol):
            try:
                sample = sync_manager.sample_spread(symbol)
                notify("info", f"Spread for {symbol}: {sample.spread}.")
            except MT5Error as exc:
                notify("error", str(exc))
            st.rerun()
        history = sync_manager.spread_history(symbol, limit=50) if symbol else []
        if history:
            st.dataframe(
                [{"Time": s.sampled_at.isoformat(timespec="seconds"), "Bid": s.bid, "Ask": s.ask, "Spread": s.spread} for s in history],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No spread samples yet for this symbol.")

    with book_tab:
        if st.button("Sync Market Book", key="mts_sync_book", disabled=not symbol):
            run = sync_manager.sync_market_book(symbol)
            st.session_state.mts_last_book_run = run
            notify("info" if run.status.value == "COMPLETED" else "error", f"Market Book sync: {run.status.value} ({run.records_synced} level(s)).")
            st.rerun()
        if st.session_state.get("mts_last_book_run"):
            st.json(st.session_state.mts_last_book_run.to_dict())
        st.caption("An empty book is a normal outcome -- not every symbol/broker exposes depth-of-market.")

    with sessions_tab:
        if st.button("Compute Sessions", key="mts_compute_sessions"):
            st.session_state.mts_sessions = sync_manager.compute_sessions()
            st.rerun()
        sessions = st.session_state.get("mts_sessions") or sync_manager.compute_sessions()
        st.dataframe(
            [{"Session": w.name, "UTC Open": w.utc_open.isoformat(), "UTC Close": w.utc_close.isoformat(), "Active": w.is_active} for w in sessions],
            use_container_width=True,
            hide_index=True,
        )

    with stats_tab:
        stats = sync_manager.get_statistics()
        render_info_card("Sync Statistics", [
            ("Total Runs", stats.total_runs),
            ("Success", stats.success_count),
            ("Failures", stats.failure_count),
            ("Average Latency (ms)", f"{stats.average_latency_ms:.2f}"),
            ("Last Run", stats.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if stats.last_run_at else "—"),
        ])
        if stats.runs_by_kind:
            st.dataframe([{"Kind": k, "Runs": v} for k, v in sorted(stats.runs_by_kind.items())], use_container_width=True, hide_index=True)

    with diagnostics_tab:
        if st.button("Run Diagnostics", key="mts_run_diagnostics"):
            report = sync_manager.run_diagnostics()
            st.session_state.mts_last_diagnostics = [(s.name, s.passed, s.detail) for s in report.steps]
            st.rerun()
        rows = st.session_state.get("mts_last_diagnostics")
        if rows:
            st.dataframe([{"Step": n, "Passed": p, "Detail": d} for n, p, d in rows], use_container_width=True, hide_index=True)
        else:
            st.caption("Run diagnostics to see connection + sync-layer checks.")

    with audit_tab:
        all_events = sync_manager.list_audit_events(limit=100)
        if all_events:
            st.dataframe(
                [{"Event": e.event_type.value, "Key": e.key, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in all_events],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No sync audit events yet.")

    with health_tab:
        health = sync_manager.get_health()
        cols = st.columns(3)
        cols[0].metric("Overall Status", health.overall_status)
        cols[1].metric("Total Runs", health.total_runs)
        cols[2].metric("Avg Latency (ms)", f"{health.average_latency_ms:.2f}")
        if health.per_kind:
            st.dataframe(
                [{"Kind": k.kind, "Last Status": k.last_status, "Runs": k.run_count, "Failures": k.failure_count} for k in health.per_kind],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No sync runs recorded yet.")

with info_col:
    st.subheader("Information")
    render_info_card("MT5 Data Sync", [
        ("Connection State", mt5_manager.connection_state.value),
        ("Selected Symbol", symbol or "—"),
        ("Total Sync Runs", sync_manager.get_statistics().total_runs),
    ])

render_status_bar(
    module="MT5 Data Synchronization",
    execution_status="Connected" if mt5_manager.connection_state == ConnectionState.CONNECTED else mt5_manager.connection_state.value,
    **job_manager.status_counts(),
)
