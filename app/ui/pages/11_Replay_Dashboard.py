"""
Streamlit page: Replay Dashboard.

Replay historical candles exactly as they occurred, optionally overlaying
an already-built strategy's indicators/detections and an already-run
backtest's trade lifecycle -- purely for visualization. This page (and
the module behind it) never modifies strategy logic, never optimizes,
never executes a trade, and never connects to a broker or MT5.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.replay_engine import ReplayConfiguration, ReplayEngine, ReplayEventType, ReplayReport, ReplaySerializer, ReplaySpeed
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext

st.set_page_config(page_title="Replay Dashboard - QuantForge AI", page_icon="🎬", layout="wide")

st.title("Replay Dashboard")
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

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("1. Historical Data (required)")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

st.sidebar.header("2. Strategy Overlay (optional)")
overlay_strategy = st.sidebar.checkbox("Overlay a strategy's indicators + a backtest's trades", value=True)

st.sidebar.header("3. Replay Scope")
default_speed_label = st.sidebar.selectbox("Default speed", [s.name for s in ReplaySpeed])

if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to start a replay.")
    st.stop()

import tempfile

with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = Path(tmp.name)

try:
    data = loader.load_csv(tmp_path, clean=True)
except CSVFormatError as exc:
    st.error(f"Could not load historical data: {exc}")
    st.stop()
finally:
    tmp_path.unlink(missing_ok=True)

st.sidebar.success(f"Loaded {len(data)} candle(s).")

strategy_model = None
backtest_result = None
indicator_engine = IndicatorEngine(registry=st.session_state.indicator_registry)
smart_money_engine = SmartMoneyEngine(registry=st.session_state.smc_registry)

if overlay_strategy:
    examples = _load_examples()
    choice = st.sidebar.selectbox("SDL example", list(examples.keys()))
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
                st.sidebar.success(f"Built '{strategy_model.metadata.name}'")

                symbol = strategy_model.context_requirement.symbols[0]
                timeframe = strategy_model.context_requirement.timeframes[0]
                bt_configuration = BacktestConfiguration(symbol=symbol, timeframe=timeframe, stop_loss_points=2.0, take_profit_points=4.0)
                bt_context = BacktestContext(
                    strategy_model=strategy_model, data=data, configuration=bt_configuration,
                    indicator_engine=indicator_engine, smart_money_engine=smart_money_engine,
                )
                with st.spinner("Running the backtest to overlay trade markers..."):
                    bt_session = BacktestRunner().try_execute(bt_context)
                if bt_session.is_successful:
                    backtest_result = bt_session.result
                    st.sidebar.success(f"Backtest produced {len(backtest_result.trades)} trade(s).")
            else:
                st.sidebar.warning("Strategy failed Strategy Builder validation; replaying candles only.")
    except SDLParseError as exc:
        st.sidebar.warning(f"Could not parse example: {exc}")

symbol = strategy_model.context_requirement.symbols[0] if strategy_model else "SYMBOL"
timeframe = strategy_model.context_requirement.timeframes[0] if strategy_model else "TF"

replay_configuration = ReplayConfiguration(symbol=symbol, timeframe=timeframe, default_speed=ReplaySpeed[default_speed_label])
replay_engine = ReplayEngine()

if "controller" not in st.session_state or st.sidebar.button("(Re)start Replay", type="primary"):
    try:
        st.session_state.controller = replay_engine.create_controller(
            data, replay_configuration, strategy_model=strategy_model, indicator_engine=indicator_engine,
            smart_money_engine=smart_money_engine, backtest_result=backtest_result,
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced to the user, not swallowed
        st.error(f"Could not prepare replay: {exc}")
        st.stop()

controller = st.session_state.controller

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

tabs = st.tabs(["Frame Viewer", "Trade Viewer", "Timeline Viewer", "Replay Report"])

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

with st.expander("Prepared ReplayResult (JSON)"):
    if st.button("Compile ReplayResult"):
        session = replay_engine.try_execute(
            data, replay_configuration, strategy_model=strategy_model, indicator_engine=indicator_engine,
            smart_money_engine=smart_money_engine, backtest_result=backtest_result,
        )
        if session.is_successful:
            report = ReplayReport(session.result)
            st.json(report.replay_summary())
            st.code(ReplaySerializer().to_json(session.result), language="json")
        else:
            st.error("Invalid:")
            st.code(session.validation.report())
