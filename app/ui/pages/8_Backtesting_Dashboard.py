"""
Streamlit page: Backtesting Dashboard.

Build an executable strategy from SDL, load historical OHLCV data, run a
deterministic historical replay, and inspect the resulting performance
summary, trade list, trade journal, equity/balance curves, drawdown
report, and execution timeline. Phase 9 scope only -- this page (and the
module behind it) never connects to a broker, places a live order, or
requires MetaTrader.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestingEngine, TradeJournal
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext

st.set_page_config(page_title="Backtesting Dashboard - QuantForge AI", page_icon="📊", layout="wide")

st.title("Backtesting Dashboard")
st.caption(
    "Deterministic, candle-by-candle historical replay of a compiled strategy. "
    "This module never connects to a broker, places a live order, or requires MetaTrader."
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


st.sidebar.header("1. Strategy")
examples = _load_examples()
choice = st.sidebar.selectbox("SDL example", list(examples.keys()))

try:
    raw_data = parser.parse_file(examples[choice])
except SDLParseError as exc:
    st.error(f"Could not parse example: {exc}")
    st.stop()

sdl_result = SDLValidator().validate(raw_data)
if not sdl_result.is_valid:
    st.error("This SDL document is invalid at the SDL layer (Phase 4):")
    st.code(sdl_result.report())
    st.stop()

strategy_context = StrategyContext(
    sdl_definition=sdl_result.definition,
    indicator_registry=st.session_state.indicator_registry,
    smc_registry=st.session_state.smc_registry,
)
build_result = strategy_builder.try_build(strategy_context)

if not build_result.is_valid:
    st.error("This strategy failed Strategy Builder validation (Phase 8):")
    st.code(build_result.validation.report())
    st.stop()

model = build_result.model
st.sidebar.success(f"Built '{model.metadata.name}'")

st.sidebar.header("2. Historical Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

st.sidebar.header("3. Execution Assumptions")
symbol = st.sidebar.selectbox("Symbol", model.context_requirement.symbols)
timeframe = st.sidebar.selectbox("Timeframe", model.context_requirement.timeframes)
initial_balance = st.sidebar.number_input("Initial balance", min_value=1.0, value=10_000.0, step=1000.0)
lot_size = st.sidebar.number_input("Lot size", min_value=0.01, value=1.0, step=0.1)
spread_points = st.sidebar.number_input("Spread (points)", min_value=0.0, value=0.0, step=0.1)
slippage_points = st.sidebar.number_input("Slippage (points)", min_value=0.0, value=0.0, step=0.1)
commission_per_lot = st.sidebar.number_input("Commission per lot", min_value=0.0, value=0.0, step=0.5)
stop_loss_points = st.sidebar.number_input("Stop loss (points, 0 = none)", min_value=0.0, value=0.0, step=0.5)
take_profit_points = st.sidebar.number_input("Take profit (points, 0 = none)", min_value=0.0, value=0.0, step=0.5)

if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to run a backtest.")
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = Path(tmp.name)

try:
    data = loader.load_csv(tmp_path, clean=True)
except CSVFormatError as exc:
    st.error(f"Could not load historical data: {exc}")
    st.stop()

configuration = BacktestConfiguration(
    symbol=symbol,
    timeframe=timeframe,
    initial_balance=initial_balance,
    lot_size=lot_size,
    spread_points=spread_points,
    slippage_points=slippage_points,
    commission_per_lot=commission_per_lot,
    stop_loss_points=stop_loss_points or None,
    take_profit_points=take_profit_points or None,
)

engine = BacktestingEngine(
    indicator_engine=IndicatorEngine(registry=st.session_state.indicator_registry),
    smart_money_engine=SmartMoneyEngine(registry=st.session_state.smc_registry),
)

if st.sidebar.button("Run Backtest", type="primary"):
    st.session_state.backtest_session = engine.try_execute(model, data, configuration)

if "backtest_session" not in st.session_state:
    st.stop()

session = st.session_state.backtest_session

st.subheader("Validation Report")
if session.is_successful:
    st.success(f"Valid ({len(session.validation.warnings)} warning(s))")
else:
    st.error(f"Invalid ({len(session.validation.errors)} error(s))")
for issue in session.validation.errors:
    st.markdown(f"- 🔴 **{issue.path}** — {issue.message}")
for issue in session.validation.warnings:
    st.markdown(f"- 🟡 **{issue.path}** — {issue.message}")

if not session.is_successful:
    st.stop()

result = session.result
journal = TradeJournal(result.trades)

st.subheader("Performance Summary")
stats = result.statistics
row1 = st.columns(5)
row1[0].metric("Total trades", stats.total_trades)
row1[1].metric("Win rate", f"{stats.win_rate:.1f}%")
row1[2].metric("Net profit", f"{stats.net_profit:,.2f}")
row1[3].metric("Profit factor", f"{stats.profit_factor:.2f}" if stats.profit_factor is not None else "—")
row1[4].metric("Expectancy", f"{stats.expectancy:,.2f}")
row2 = st.columns(5)
row2[0].metric("Max drawdown", f"{result.drawdown_report.max_drawdown:,.2f}")
row2[1].metric("Max drawdown %", f"{result.drawdown_report.max_drawdown_pct:.1f}%")
row2[2].metric("Sharpe (framework)", f"{stats.sharpe_ratio:.2f}" if stats.sharpe_ratio is not None else "—")
row2[3].metric("Sortino (framework)", f"{stats.sortino_ratio:.2f}" if stats.sortino_ratio is not None else "—")
row2[4].metric("Calmar (framework)", f"{stats.calmar_ratio:.2f}" if stats.calmar_ratio is not None else "—")
st.caption(f"Checksum: {result.checksum}")

st.subheader("Equity Curve")
equity_df = pd.DataFrame({p.datetime: p.equity for p in result.equity_curve.points}.items(), columns=["datetime", "equity"])
st.line_chart(equity_df.set_index("datetime"))

st.subheader("Balance Curve")
balance_df = pd.DataFrame({p.datetime: p.balance for p in result.balance_curve.points}.items(), columns=["datetime", "balance"])
st.line_chart(balance_df.set_index("datetime"))

st.subheader("Drawdown Viewer")
drawdown_df = pd.DataFrame(
    {p.datetime: p.drawdown_pct for p in result.drawdown_report.points}.items(), columns=["datetime", "drawdown_pct"]
)
st.area_chart(drawdown_df.set_index("datetime"))

st.subheader("Trade List")
st.dataframe(journal.to_dataframe(), use_container_width=True, hide_index=True)

st.subheader("Trade Journal")
st.json(journal.summary())

st.subheader("Execution Timeline")
timeline_rows = [{"index": e.index, "datetime": e.datetime, "event": e.event_type, "message": e.message} for e in result.execution_timeline]
st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)

with st.expander("Raw BacktestResult (JSON)"):
    from app.backtesting_engine import BacktestSerializer

    st.code(BacktestSerializer().to_json(result), language="json")
