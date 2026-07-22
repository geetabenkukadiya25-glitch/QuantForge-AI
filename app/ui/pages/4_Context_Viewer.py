"""
Streamlit page: Context Viewer.

Build a Market Context snapshot from manually entered facts, inspect its
validation report, view registered feature flags, and browse previously
saved snapshots. Phase 5 scope only -- no indicators, strategy logic,
AI, backtesting, optimization, replay, or execution.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of page-level tabs as primary navigation. The "Registered Context
Snapshots" list (formerly its own tab) is now the Explorer's scrollable
list; "Current Context" (build form) and "Feature Flags" remain Workspace
tabs. No `MarketContextEngine`/`FeatureFlagManager` call changed -- only
where each already-existing block renders.
"""

from datetime import datetime, timezone

import streamlit as st

from app.context_engine import (
    ContextRegistryError,
    ContextValidationError,
    MarketContextEngine,
)
from app.context_engine.builder import MARKET_STATE_PLACEHOLDERS_FLAG
from app.core.feature_flags import FeatureFlagManager
from app.ui.components import ToolbarAction, render_command_bar, render_info_card, render_list_card, render_notification_center, render_shell, render_status_bar, render_toolbar

st.set_page_config(page_title="Context Viewer - QuantForge AI", page_icon="🧭", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Context Viewer")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Context Viewer")
st.caption("Build and inspect standardized Market Context snapshots. This engine never generates trading signals.")

if "feature_flags" not in st.session_state:
    st.session_state.feature_flags = FeatureFlagManager()
if "context_engine" not in st.session_state:
    st.session_state.context_engine = MarketContextEngine(feature_flags=st.session_state.feature_flags)

engine: MarketContextEngine = st.session_state.context_engine
flags: FeatureFlagManager = st.session_state.feature_flags
if not flags.is_registered(MARKET_STATE_PLACEHOLDERS_FLAG.name):
    flags.register(MARKET_STATE_PLACEHOLDERS_FLAG)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    st.markdown("**Registered Context Snapshots**")
    summaries = engine.list_snapshots()

    def _render_snapshot_card(summary) -> None:
        with st.container(border=True):
            st.write(f"**{summary.symbol} {summary.timeframe}** @ {summary.datetime_utc}")
            st.caption(f"{summary.snapshot_id} · v{summary.context_version}")
            if st.button("Delete", key=f"delete_{summary.snapshot_id}", use_container_width=True):
                engine.delete(summary.snapshot_id)
                st.rerun()

    render_list_card("", summaries, _render_snapshot_card, empty_caption="No snapshots saved yet. Build and save one in the Workspace.")

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("💾 Save", "save", type="primary"),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically after building a snapshot."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Use the Explorer's Registered Context Snapshots list."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    tab_build, tab_flags = st.tabs(["Current Context", "Feature Flags"])

    with tab_build:
        st.subheader("Build a Context Snapshot")
        with st.form("build_context_form"):
            col1, col2 = st.columns(2)
            with col1:
                symbol = st.text_input("Symbol", value="EURUSD")
                timeframe = st.text_input("Timeframe", value="H1")
                candle_index = st.number_input("Candle index", min_value=0, value=0, step=1)
                date_value = st.date_input("Date (UTC)")
                time_value = st.time_input("Time (UTC)")
            with col2:
                digits = st.number_input("Digits", min_value=0, value=5, step=1)
                point = st.number_input("Point", min_value=0.0, value=0.00001, format="%.5f")
                tick_size = st.number_input("Tick size", min_value=0.0, value=0.00001, format="%.5f")
                tick_value = st.number_input("Tick value", min_value=0.0, value=1.0)
                spread = st.number_input("Spread", min_value=0.0, value=1.2)
                contract_size = st.number_input("Contract size", min_value=0.0, value=100000.0)
                currency = st.text_input("Currency", value="USD")

            submitted = st.form_submit_button("Build context")

        if submitted:
            moment = datetime.combine(date_value, time_value, tzinfo=timezone.utc)
            symbol_spec = {
                "digits": int(digits),
                "point": point,
                "tick_size": tick_size,
                "tick_value": tick_value,
                "spread": spread,
                "contract_size": contract_size,
                "currency": currency,
            }
            try:
                snapshot = engine.build_context(
                    symbol=symbol,
                    timeframe=timeframe,
                    current_datetime=moment,
                    candle_index=int(candle_index),
                    symbol_spec=symbol_spec,
                )
            except ContextValidationError as exc:
                st.error(f"Validation failed: {exc}")
            else:
                st.session_state.last_snapshot = snapshot
                st.success(f"Built snapshot {snapshot.snapshot_id}")

        snapshot = st.session_state.get("last_snapshot")
        if snapshot is not None:
            result = engine.validate(snapshot)
            st.markdown("### Validation Report")
            if result.is_valid:
                st.success(f"Valid ({len(result.warnings)} warning(s))")
            else:
                st.error(f"Invalid ({len(result.errors)} error(s))")
            for issue in result.errors:
                st.markdown(f"- 🔴 **{issue.path}** — {issue.message}")
            for issue in result.warnings:
                st.markdown(f"- 🟡 **{issue.path}** — {issue.message}")

            st.markdown("### Snapshot")
            st.json(snapshot.model_dump(mode="json"), expanded=False)

            if toolbar_clicked.get("save"):
                try:
                    path = engine.save(snapshot)
                except ContextRegistryError as exc:
                    st.error(f"Could not save: {exc}")
                else:
                    st.success(f"Saved to {path}")

    with tab_flags:
        st.subheader("Feature Flags")
        for status in flags.list_flags():
            cols = st.columns([3, 2, 2, 3])
            cols[0].write(f"**{status.name}**")
            cols[1].write(status.stage.value)
            cols[2].write("🟢 enabled" if status.enabled else "⚪ disabled")
            cols[3].write(f"source: {status.source}")

        st.divider()
        flag_name = st.selectbox("Toggle a flag", [f.name for f in flags.list_flags()])
        toggle_col1, toggle_col2 = st.columns(2)
        if toggle_col1.button("Enable"):
            flags.enable(flag_name)
            st.rerun()
        if toggle_col2.button("Disable"):
            flags.disable(flag_name)
            st.rerun()

with info_col:
    st.subheader("Information")
    last_snapshot = st.session_state.get("last_snapshot")
    if last_snapshot is not None:
        render_info_card(
            "Current Snapshot",
            [
                ("Snapshot ID", last_snapshot.snapshot_id),
                ("Symbol", last_snapshot.symbol),
                ("Timeframe", last_snapshot.timeframe),
            ],
        )
    else:
        st.caption("Nothing built yet.")
    render_info_card("Registry", [("Saved snapshots", len(summaries))])

render_status_bar(
    module="Context Viewer",
    execution_status="Ready",
)
