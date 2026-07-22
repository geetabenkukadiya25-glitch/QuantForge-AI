"""
Streamlit page: Replay Dashboard.

Replay historical candles exactly as they occurred, optionally overlaying
an already-built strategy's indicators/detections and an already-run
backtest's trade lifecycle -- purely for visualization. This page (and
the module behind it) never modifies strategy logic, never optimizes,
never executes a trade, and never connects to a broker or MT5.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar and a
bottom status bar. Its existing results tabs (Frame/Trade/Timeline/Report
Viewer) are unchanged, plus a new Export tab hosting what used to be the
"Prepared ReplayResult (JSON)" expander. No engine, SDL, Replay Engine, or
Backtesting Engine call changed -- every `st.sidebar.X(...)` became
`st.X(...)` inside a `with explorer_col:` block, and "(Re)start Replay"
moved into the toolbar as "Run".

Phase 18.4: the interactive `controller` (Play/Pause/step) stays fully
synchronous -- it's a live, stateful object the user manipulates on every
click, not a batch operation, so it's a poor fit for the Job Manager.
What DOES become a Job is "Compile ReplayResult" (Export tab): building
the full `ReplayResult` report is the one true "run once, get a result"
operation on this page, so it now goes through `JobManager.submit(...)`
like every other dashboard's primary action.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
from app.replay_engine import ReplayConfiguration, ReplayEngine, ReplayEventType, ReplayReport, ReplaySerializer, ReplaySpeed
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar
from app.ui.progress import ProgressTracker, REPLAY_STEPS, tracked_step

st.set_page_config(page_title="Replay Dashboard - QuantForge AI", page_icon="🎬", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Replay Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Replay Dashboard")
st.caption(
    "Candle-by-candle historical replay. This module never modifies strategy logic, never optimizes, "
    "never executes a trade, and never connects to a broker or MT5."
)

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()

parser = StrategyParser()
strategy_builder = StrategyBuilder()
loader = DataLoader()
job_manager = get_job_manager()

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


explorer_col, workspace_col, info_col = render_shell()

with info_col:
    st.subheader("Information")

with explorer_col:
    st.subheader("Explorer")
    st.header("1. Historical Data (required)")
    uploaded_file = st.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

    st.header("2. Strategy Overlay (optional)")
    overlay_strategy = st.checkbox("Overlay a strategy's indicators + a backtest's trades", value=True)

    st.header("3. Replay Scope")
    default_speed_label = st.selectbox("Default speed", [s.name for s in ReplaySpeed])

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary"),
            ToolbarAction("⏹ Stop", "stop", enabled=False, disabled_reason="Use the Pause control in Replay Controls below."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for the overlay strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Compilation runs automatically for the overlay strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Replay in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    if uploaded_file is None:
        st.info("Upload historical OHLCV data in the Explorer to start a replay.")
        render_status_bar(module="Replay Dashboard", execution_status="Awaiting Data")
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        data = loader.load_csv(tmp_path, clean=True)
    except CSVFormatError as exc:
        st.error(f"Could not load historical data: {exc}")
        render_status_bar(module="Replay Dashboard", execution_status="Data Error")
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

    st.success(f"Loaded {len(data)} candle(s).")

    strategy_model = None
    backtest_result = None
    indicator_engine = IndicatorEngine(registry=st.session_state.indicator_registry)
    smart_money_engine = SmartMoneyEngine(registry=st.session_state.smc_registry)

    if overlay_strategy:
        examples = _load_examples()
        choice = st.selectbox("SDL example", list(examples.keys()))
        try:
            raw_data = parser.parse_file(examples[choice])
            sdl_result = SDLValidator().validate(raw_data)
            if sdl_result.is_valid:
                strategy_context = StrategyContext(
                    sdl_definition=sdl_result.definition, indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry
                )
                build_result = strategy_builder.try_build(strategy_context)
                if build_result.is_valid:
                    strategy_model = build_result.model
                    st.success(f"Built '{strategy_model.metadata.name}'")

                    progress_placeholder = st.empty()
                    tracker = ProgressTracker(REPLAY_STEPS)
                    with tracked_step(tracker, 0, progress_placeholder):
                        symbol = strategy_model.context_requirement.symbols[0]
                        timeframe = strategy_model.context_requirement.timeframes[0]
                        bt_configuration = BacktestConfiguration(symbol=symbol, timeframe=timeframe, stop_loss_points=2.0, take_profit_points=4.0)
                        bt_context = BacktestContext(
                            strategy_model=strategy_model, data=data, configuration=bt_configuration,
                            indicator_engine=indicator_engine, smart_money_engine=smart_money_engine,
                        )
                    with tracked_step(tracker, 1, progress_placeholder):
                        bt_session = BacktestRunner().try_execute(bt_context)
                    if bt_session.is_successful:
                        backtest_result = bt_session.result
                        st.success(f"Backtest produced {len(backtest_result.trades)} trade(s).")
                else:
                    st.warning("Strategy failed Strategy Builder validation; replaying candles only.")
        except SDLParseError as exc:
            st.warning(f"Could not parse example: {exc}")

    symbol = strategy_model.context_requirement.symbols[0] if strategy_model else "SYMBOL"
    timeframe = strategy_model.context_requirement.timeframes[0] if strategy_model else "TF"

    replay_configuration = ReplayConfiguration(symbol=symbol, timeframe=timeframe, default_speed=ReplaySpeed[default_speed_label])
    replay_engine = ReplayEngine()

    if "controller" not in st.session_state or toolbar_clicked.get("run"):
        try:
            st.session_state.controller = replay_engine.create_controller(
                data, replay_configuration, strategy_model=strategy_model, indicator_engine=indicator_engine,
                smart_money_engine=smart_money_engine, backtest_result=backtest_result,
            )
        except Exception as exc:  # noqa: BLE001 -- surfaced to the user, not swallowed
            st.error(f"Could not prepare replay: {exc}")
            render_status_bar(module="Replay Dashboard", execution_status="Error")
            st.stop()

    controller = st.session_state.controller

with info_col:
    render_info_card(
        "Replay",
        [
            ("Candles", f"{len(data):,}"),
            ("Strategy overlay", strategy_model.metadata.name if strategy_model else "None"),
            ("Backtest trades", f"{len(backtest_result.trades):,}" if backtest_result else "—"),
        ],
    )

with workspace_col:
    st.subheader("Replay Controls")
    timeline_cols = st.columns(8)
    if timeline_cols[0].button("⏮ Beginning"):
        controller.go_to_beginning()
    if timeline_cols[1].button("◀◀ -10"):
        controller.step_backward(10)
    if timeline_cols[2].button("◀ -1"):
        controller.step_backward(1)
    if timeline_cols[3].button("▶ Play"):
        controller.play()
    if timeline_cols[4].button("⏸ Pause"):
        controller.pause()
    if timeline_cols[5].button("▶ +1"):
        controller.step_forward(1)
    if timeline_cols[6].button("▶▶ +10"):
        controller.step_forward(10)
    if timeline_cols[7].button("⏭ End"):
        controller.go_to_end()

    speed_label = st.select_slider("Speed", options=[s.name for s in ReplaySpeed], value=controller.player.speed.name)
    controller.set_speed(ReplaySpeed[speed_label])
    if controller.player.state.value == "PLAYING" and st.button("Advance one tick"):
        controller.tick()

    jump_index = st.slider("Jump to candle", min_value=0, max_value=controller.timeline.total_frames - 1, value=controller.cursor.index)
    if jump_index != controller.cursor.index:
        controller.jump_to_candle(jump_index)

    st.caption(f"State: {controller.player.state.value} | Speed: {controller.player.speed.name} | Frame {controller.cursor.index + 1} / {controller.timeline.total_frames}")

    tabs = st.tabs(["Frame Viewer", "Trade Viewer", "Timeline Viewer", "Replay Report", "Export"])

    with tabs[0]:
        frame = controller.current_frame
        cols = st.columns(5)
        cols[0].metric("Datetime", frame.datetime)
        cols[1].metric("Open", f"{frame.open:.4f}")
        cols[2].metric("High", f"{frame.high:.4f}")
        cols[3].metric("Low", f"{frame.low:.4f}")
        cols[4].metric("Close", f"{frame.close:.4f}")
        if frame.indicator_values:
            st.dataframe(pd.DataFrame([v.model_dump() for v in frame.indicator_values]), use_container_width=True, hide_index=True)
        if frame.smart_money_detections:
            st.dataframe(pd.DataFrame([d.model_dump() for d in frame.smart_money_detections]), use_container_width=True, hide_index=True)
        candles = controller.synced_candles()
        st.line_chart(candles.set_index("Datetime")[["Open", "High", "Low", "Close"]])

    with tabs[1]:
        markers = controller.synced_trade_markers()
        if markers:
            st.dataframe(pd.DataFrame([m.model_dump() for m in markers]), use_container_width=True, hide_index=True)
        else:
            st.info("No trade markers at or before the current frame.")

    with tabs[2]:
        st.dataframe(pd.DataFrame({"frame_index": range(controller.timeline.total_frames), "datetime": controller.timeline.frame_datetimes}), use_container_width=True, hide_index=True)

    with tabs[3]:
        events_df = pd.DataFrame(
            [{"event_type": e.event_type.value, "frame_index": e.frame_index, "datetime": e.datetime, "message": e.message} for e in controller.events]
        )
        st.dataframe(events_df, use_container_width=True, hide_index=True)
        st.metric("Trades opened", sum(1 for e in controller.events if e.event_type == ReplayEventType.TRADE_OPENED))
        st.metric("Trades closed", sum(1 for e in controller.events if e.event_type == ReplayEventType.TRADE_CLOSED))

    with tabs[4]:
        if st.button("Compile ReplayResult"):
            def _compile_replay_result(job, data=data, replay_configuration=replay_configuration, strategy_model=strategy_model, indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result, replay_engine=replay_engine):
                with job.progress.step(0):
                    return replay_engine.try_execute(
                        data, replay_configuration, strategy_model=strategy_model, indicator_engine=indicator_engine,
                        smart_money_engine=smart_money_engine, backtest_result=backtest_result,
                    )

            job = job_manager.submit(
                name="Compile ReplayResult",
                category=JobCategory.REPLAY,
                operation=_compile_replay_result,
                owner_page="Replay Dashboard",
                step_names=["Compiling ReplayResult"],
            )
            notify("info", f"Queued: {job.name}")
            st.session_state.replay_current_job_id = job.id
            st.rerun()

        export_job_id = st.session_state.get("replay_current_job_id")
        export_job = job_manager.get(export_job_id) if export_job_id else None
        if export_job is not None:
            render_runtime_monitor(export_job.id, strategy_label=strategy_model.metadata.name if strategy_model else None)
            if export_job.state == JobState.FAILED:
                st.error(f"Compile failed: {export_job.error}")
            elif export_job.state == JobState.COMPLETED:
                session = export_job.result
                if session.is_successful:
                    report = ReplayReport(session.result)
                    st.json(report.replay_summary())
                    export_json = ReplaySerializer().to_json(session.result)
                    st.code(export_json, language="json")
                    st.download_button("Download raw result (JSON)", data=export_json, file_name="replay_result.json", mime="application/json")
                else:
                    st.error("Invalid:")
                    st.code(session.validation.report())

render_status_bar(
    module="Replay Dashboard",
    strategy_status=strategy_model.metadata.name if strategy_model else "—",
    execution_status=controller.player.state.value.title(),
    job=export_job,
    **job_manager.status_counts(),
)
