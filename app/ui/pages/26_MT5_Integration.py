"""
Streamlit page: MT5 Integration.

The central UI for the Institutional MT5 Integration Layer (Phase
19.0) -- a REAL, READ-ONLY connection to a local MetaTrader 5 terminal
via the `MetaTrader5` package. NO order execution, NO position
modification, NO broker control anywhere on this page; every action
here maps to one of the read-only calls the layer exposes
(`connect`/`disconnect`/`terminal_info`/`account_info`/`symbols_get`/
`symbol_info`/`history`/`ticks`/`market_book`/`connection_state`/
`ping`/`health`). Never modifies Backtesting, Workflow, Risk,
Governance, Settings Center, Dataset Manager, Data Catalog, Strategy
Library, Cloud Sync, or the frozen `docs/Architecture/` documents.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `mt5_*` session-state prefix.
"""

from datetime import datetime, timedelta

import streamlit as st

from app.job_manager import get_job_manager
from app.mt5 import ConnectionState, MT5Error, get_mt5_manager
from app.mt5.exceptions import MT5SymbolNotFoundError
from app.mt5.timeframe_manager import supported_timeframes
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

st.set_page_config(page_title="MT5 Integration - QuantForge AI", page_icon="📡", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("MT5 Integration")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("MT5 Integration")
st.caption(
    "Read-only MT5 Integration Layer. Every action below maps to a read-only MetaTrader5 call "
    "(initialize/shutdown/terminal_info/account_info/symbols_get/history/ticks/market_book/ping). "
    "No order execution, no position modification, no broker control exists anywhere in this build."
)

manager = get_mt5_manager()
job_manager = get_job_manager()

st.session_state.setdefault("mt5_selected_symbol", "")

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    state = manager.connection_state
    with st.container(border=True):
        st.markdown(f"**Connection State:** {state.value}")
        if state == ConnectionState.CONNECTED:
            st.caption("Connected -- read-only calls are live.")
        else:
            st.caption("Not connected -- use the toolbar to connect.")

    st.markdown("**Symbol**")
    symbols = manager.list_symbols() if state == ConnectionState.CONNECTED else []
    symbol_names = [s.name for s in symbols]
    if symbol_names:
        default_index = symbol_names.index(st.session_state.mt5_selected_symbol) if st.session_state.mt5_selected_symbol in symbol_names else 0
        chosen = st.selectbox("Select a symbol", symbol_names, index=default_index, key="mt5_symbol_select")
        st.session_state.mt5_selected_symbol = chosen
    else:
        st.caption("Connect to browse symbols.")
        st.text_input("Symbol (manual)", key="mt5_selected_symbol")

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("🔌 Connect", "connect", enabled=state != ConnectionState.CONNECTED),
            ToolbarAction("🔴 Disconnect", "disconnect", enabled=state == ConnectionState.CONNECTED),
            ToolbarAction("🔄 Reconnect", "reconnect", enabled=state in (ConnectionState.LOST, ConnectionState.TERMINAL_NOT_RUNNING, ConnectionState.DISCONNECTED)),
            ToolbarAction("📶 Ping", "ping", enabled=state == ConnectionState.CONNECTED),
        ]
    )

    try:
        if toolbar_clicked.get("connect"):
            new_state = manager.connect()
            if new_state == ConnectionState.CONNECTED:
                notify("info", "Connected to MT5 terminal.")
            else:
                notify("warning", f"Connection attempt resulted in: {new_state.value}.")
            st.rerun()
        if toolbar_clicked.get("disconnect"):
            manager.disconnect()
            notify("info", "Disconnected.")
            st.rerun()
        if toolbar_clicked.get("reconnect"):
            new_state = manager.reconnect()
            notify("info" if new_state == ConnectionState.CONNECTED else "warning", f"Reconnect result: {new_state.value}.")
            st.rerun()
        if toolbar_clicked.get("ping"):
            latency = manager.ping()
            notify("info", f"Ping: {latency:.1f} ms.")
            st.rerun()
    except MT5Error as exc:
        notify("error", str(exc))

    tabs = st.tabs(["Overview", "Connection", "Terminal", "Account", "Symbols", "Market Watch", "History", "Ticks", "Diagnostics", "Bridge", "Audit", "Settings", "Health"])
    (
        overview_tab, connection_tab, terminal_tab, account_tab, symbols_tab, market_watch_tab,
        history_tab, ticks_tab, diagnostics_tab, bridge_tab, audit_tab, settings_tab, health_tab,
    ) = tabs

    with overview_tab:
        st.markdown(f"**Connection State:** {manager.connection_state.value}")
        if manager.connection_state == ConnectionState.CONNECTED:
            try:
                account = manager.get_account_info()
                cols = st.columns(4)
                cols[0].metric("Balance", f"{account.balance:,.2f} {account.currency}")
                cols[1].metric("Equity", f"{account.equity:,.2f} {account.currency}")
                cols[2].metric("Margin Free", f"{account.margin_free:,.2f} {account.currency}")
                cols[3].metric("Leverage", f"1:{account.leverage}")
            except MT5Error as exc:
                st.caption(f"Account info unavailable: {exc}")
            st.markdown(f"**Symbols Available:** {len(manager.list_symbols())}")
        else:
            st.caption("Connect to see account and symbol counts.")

    with connection_tab:
        st.markdown(f"**State:** {manager.connection_state.value}")
        st.caption("Supported states: Disconnected, Connecting, Connected, Lost, Reconnecting, Unsupported Version, Terminal Not Running, Permission Denied.")
        discovered = manager.discover_terminals()
        if discovered:
            st.markdown("**Discovered Terminal Executables**")
            for path in discovered:
                st.caption(str(path))
        else:
            st.caption("No terminal executables found in common install locations -- initialize() may still locate one automatically.")
        try:
            compat = manager.compatibility()
            st.markdown(f"**Package Version:** {compat.package_version} ({'supported' if compat.package_supported else 'unverified'})")
            if compat.terminal_build is not None:
                st.markdown(f"**Terminal Build:** {compat.terminal_build} ({'supported' if compat.terminal_supported else 'below minimum verified build'})")
            for note in compat.notes:
                st.caption(note)
        except MT5Error as exc:
            st.caption(f"Compatibility check unavailable: {exc}")

    with terminal_tab:
        if manager.connection_state == ConnectionState.CONNECTED:
            try:
                info = manager.get_terminal_info()
                render_info_card("Terminal", [
                    ("Name", info.name), ("Company", info.company), ("Build", info.build),
                    ("Path", info.path), ("Data Path", info.data_path),
                    ("Connected", info.connected), ("Trade Allowed", info.trade_allowed), ("Trade Expert (EA)", info.trade_expert),
                ])
            except MT5Error as exc:
                st.caption(f"Terminal info unavailable: {exc}")
        else:
            st.caption("Connect to see terminal information.")

    with account_tab:
        if manager.connection_state == ConnectionState.CONNECTED:
            try:
                account = manager.get_account_info()
                render_info_card("Account (read-only)", [
                    ("Login", account.login), ("Server", account.server), ("Currency", account.currency),
                    ("Balance", account.balance), ("Equity", account.equity),
                    ("Margin", account.margin), ("Margin Free", account.margin_free),
                    ("Leverage", f"1:{account.leverage}"), ("Trade Allowed", account.trade_allowed),
                ])
            except MT5Error as exc:
                st.caption(f"Account info unavailable: {exc}")
        else:
            st.caption("Connect to see account information.")

    with symbols_tab:
        if manager.connection_state == ConnectionState.CONNECTED:
            symbol_query = st.text_input("Filter symbols", key="mt5_symbol_filter")
            rows = [s for s in symbols if symbol_query.lower() in s.name.lower()] if symbol_query else symbols
            if rows:
                st.dataframe(
                    [{"Symbol": s.name, "Description": s.description, "Digits": s.digits, "Spread": s.spread, "Visible": s.visible} for s in rows[:200]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No symbols match.")
        else:
            st.caption("Connect to browse symbols.")

    with market_watch_tab:
        symbol = st.session_state.mt5_selected_symbol
        if manager.connection_state == ConnectionState.CONNECTED and symbol:
            try:
                quote = manager.get_quote(symbol)
                cols = st.columns(3)
                cols[0].metric("Bid", quote.bid)
                cols[1].metric("Ask", quote.ask)
                cols[2].metric("Spread", round(quote.ask - quote.bid, 6))
            except MT5SymbolNotFoundError as exc:
                st.caption(str(exc))
            depth = manager.get_market_depth(symbol)
            if depth:
                st.dataframe([{"Type": d.type_, "Price": d.price, "Volume": d.volume} for d in depth], use_container_width=True, hide_index=True)
            else:
                st.caption("No market depth available for this symbol/broker.")
        else:
            st.caption("Connect and select a symbol to see live quotes.")

    with history_tab:
        symbol = st.session_state.mt5_selected_symbol
        with st.form("mt5_history_form"):
            timeframe = st.selectbox("Timeframe", supported_timeframes(), index=supported_timeframes().index("H1"))
            days_back = st.number_input("Days back", min_value=1, value=7)
            submitted = st.form_submit_button("Sync History", disabled=manager.connection_state != ConnectionState.CONNECTED or not symbol)
            if submitted:
                date_to = datetime.now()
                date_from = date_to - timedelta(days=int(days_back))
                job = manager.submit_history_sync(symbol, timeframe, date_from, date_to, owner_page="MT5 Integration")
                st.session_state.mt5_last_history_job_id = job.id
                notify("info", f"History sync submitted for {symbol} {timeframe}.")
                st.rerun()
        job_id = st.session_state.get("mt5_last_history_job_id")
        if job_id:
            job = job_manager.get(job_id)
            if job is not None:
                st.markdown(f"**Last History Sync Job:** {job.state.value}")
                if job.result:
                    bars = job.result
                    st.dataframe(
                        [{"Time": b.time.isoformat(), "Open": b.open, "High": b.high, "Low": b.low, "Close": b.close, "Volume": b.tick_volume} for b in bars[-100:]],
                        use_container_width=True,
                        hide_index=True,
                    )

    with ticks_tab:
        symbol = st.session_state.mt5_selected_symbol
        with st.form("mt5_ticks_form"):
            minutes_back = st.number_input("Minutes back", min_value=1, value=5)
            submitted = st.form_submit_button("Sync Ticks", disabled=manager.connection_state != ConnectionState.CONNECTED or not symbol)
            if submitted:
                date_to = datetime.now()
                date_from = date_to - timedelta(minutes=int(minutes_back))
                job = manager.submit_tick_sync(symbol, date_from, date_to, owner_page="MT5 Integration")
                st.session_state.mt5_last_tick_job_id = job.id
                notify("info", f"Tick sync submitted for {symbol}.")
                st.rerun()
        job_id = st.session_state.get("mt5_last_tick_job_id")
        if job_id:
            job = job_manager.get(job_id)
            if job is not None:
                st.markdown(f"**Last Tick Sync Job:** {job.state.value}")
                if job.result:
                    ticks = job.result
                    st.dataframe(
                        [{"Time": t.time.isoformat(), "Bid": t.bid, "Ask": t.ask, "Volume": t.volume} for t in ticks[-200:]],
                        use_container_width=True,
                        hide_index=True,
                    )

    with diagnostics_tab:
        if st.button("Run Diagnostics", key="mt5_run_diagnostics"):
            report = manager.run_diagnostics()
            st.session_state.mt5_last_diagnostics = [(s.name, s.passed, s.detail) for s in report.steps]
        diagnostics_rows = st.session_state.get("mt5_last_diagnostics")
        if diagnostics_rows:
            st.dataframe(
                [{"Step": name, "Passed": passed, "Detail": detail} for name, passed, detail in diagnostics_rows],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Run diagnostics to see package, discovery, connection, and symbol checks.")

    with bridge_tab:
        from app.mt5.bridge_manager import list_transports, preview_payload, schema_version

        st.markdown(f"**Bridge Schema Version:** {schema_version()}")
        st.caption("Future compatible with SMC GOLD AI TRADER PRO. Bridge only -- no execution, no live transport this phase.")
        st.json(preview_payload())
        for transport in list_transports():
            with st.container(border=True):
                st.markdown(f"**{transport.display_name}**")
                st.caption(transport.description)
                st.button("Connect Bridge Transport", key=f"mt5_connect_{transport.display_name}", disabled=True, help="Not implemented -- no real IPC/network transport exists in this build.")

    with audit_tab:
        events = manager.list_audit_events()
        if events:
            st.dataframe(
                [{"Event": e.event_type.value, "Key": e.key, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in events],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No audit events yet.")

    with settings_tab:
        st.info("Broader platform settings live in Settings Center -- this tab only covers MT5's own local connection preferences (auto-connect, retry interval, terminal path override), which are not routed through Settings Center.")
        current = manager.get_settings()
        with st.form("mt5_settings_form"):
            auto_connect = st.checkbox("Auto-Connect (stored preference only -- nothing auto-connects yet)", value=current.auto_connect)
            retry_interval = st.number_input("Retry Interval (seconds)", min_value=5, value=current.retry_interval_seconds)
            terminal_path = st.text_input("Terminal Path Override", value=current.terminal_path_override or "")
            if st.form_submit_button("Save Settings"):
                manager.update_settings(auto_connect=auto_connect, retry_interval_seconds=int(retry_interval), terminal_path_override=terminal_path.strip() or None)
                notify("info", "MT5 settings saved.")
                st.rerun()
        if st.button("Open Settings Center", key="mt5_open_settings_center"):
            st.switch_page("pages/24_Settings_Center.py")

    with health_tab:
        health = manager.get_health_snapshot()
        cols = st.columns(3)
        cols[0].metric("Connection State", health.connection_state.value)
        cols[1].metric("Latency (ms)", f"{health.latency_ms:.2f}" if health.latency_ms is not None else "—")
        cols[2].metric("Uptime (s)", f"{health.connection_uptime_seconds:.1f}" if health.connection_uptime_seconds is not None else "—")
        render_info_card("Health Detail", [
            ("Last Heartbeat", health.last_heartbeat_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_heartbeat_at else "—"),
            ("Last Tick", health.last_tick_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_tick_at else "—"),
            ("Last History Sync", health.last_history_sync_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_history_sync_at else "—"),
            ("Last Ping", health.last_ping_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_ping_at else "—"),
            ("Terminal Build", health.terminal_build or "—"),
            ("Bridge Version", health.bridge_version),
        ])

with info_col:
    st.subheader("Information")
    render_info_card("MT5 Integration", [
        ("Connection State", manager.connection_state.value),
        ("Selected Symbol", st.session_state.mt5_selected_symbol or "—"),
        ("Audit Events", len(manager.list_audit_events())),
    ])

render_status_bar(
    module="MT5 Integration",
    execution_status="Connected" if manager.connection_state == ConnectionState.CONNECTED else manager.connection_state.value,
    **job_manager.status_counts(),
)
