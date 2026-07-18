"""
Streamlit page: Portfolio Dashboard.

Combines multiple already-backtested strategies into a single portfolio,
generating capital/risk allocation, correlation, exposure, ranking, and
portfolio-quality analytics. This page (and the module behind it) is NOT
an AI model -- it never trades, never optimizes, never validates, never
replays a chart, and never connects to a broker or MT5. It consumes ONLY
already-completed Strategy Builder / Backtesting Engine / (optionally)
Optimization Engine / Validation Engine / Replay Engine / Research Engine
outputs.
"""

import tempfile
from pathlib import Path

import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.portfolio_engine import (
    AllocationMethod,
    ManualWeight,
    PortfolioConfiguration,
    PortfolioManagementEngine,
    PortfolioReport,
    PortfolioSerializer,
    PortfolioStrategyEntry,
)
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext

st.set_page_config(page_title="Portfolio Dashboard - QuantForge AI", page_icon="📊", layout="wide")

st.title("Portfolio Dashboard")
st.caption(
    "Combines multiple already-backtested strategies into a single portfolio: allocation, correlation, "
    "exposure, ranking, and analytics. This module is NOT an AI model. It never trades, optimizes, validates, "
    "or connects to a broker or MT5 -- only aggregation over already-completed results."
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
indicator_engine = IndicatorEngine(registry=st.session_state.indicator_registry)
smart_money_engine = SmartMoneyEngine(registry=st.session_state.smc_registry)

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("1. Strategies in the Portfolio")
examples = _load_examples()
choices = st.sidebar.multiselect("SDL examples", list(examples.keys()), default=list(examples.keys())[:2])

st.sidebar.header("2. Historical Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

st.sidebar.header("3. Allocation")
allocation_method_label = st.sidebar.selectbox("Allocation method", [m.value for m in AllocationMethod])
manual_weight_inputs: dict[str, float] = {}
if allocation_method_label == AllocationMethod.MANUAL_WEIGHT.value:
    st.sidebar.caption("Manual weight per strategy (normalized automatically).")
    for name in choices:
        manual_weight_inputs[name] = st.sidebar.number_input(f"Weight: {name}", min_value=0.0, value=1.0, step=0.1, key=f"weight_{name}")

st.sidebar.header("4. Thresholds")
high_correlation_threshold = st.sidebar.slider("High correlation threshold", min_value=-1.0, max_value=1.0, value=0.7, step=0.05)
min_strategies_required = st.sidebar.number_input("Min strategies required", min_value=1, value=2, step=1)

if not choices:
    st.info("Select at least one SDL example in the sidebar.")
    st.stop()
if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to build and backtest the selected strategies.")
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = Path(tmp.name)

try:
    data = loader.load_csv(tmp_path, clean=True)
except CSVFormatError as exc:
    st.error(f"Could not load historical data: {exc}")
    st.stop()

st.sidebar.success(f"Loaded {len(data)} candle(s).")


def _build_entry(name: str) -> PortfolioStrategyEntry | None:
    try:
        raw_data = parser.parse_file(examples[name])
    except SDLParseError as exc:
        st.sidebar.warning(f"'{name}': could not parse ({exc}).")
        return None

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        st.sidebar.warning(f"'{name}': failed SDL validation, skipped.")
        return None

    strategy_context = StrategyContext(sdl_definition=sdl_result.definition, indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry)
    build_result = strategy_builder.try_build(strategy_context)
    if not build_result.is_valid:
        st.sidebar.warning(f"'{name}': failed Strategy Builder validation, skipped.")
        return None

    model = build_result.model
    symbol = model.context_requirement.symbols[0]
    timeframe = model.context_requirement.timeframes[0]
    configuration = BacktestConfiguration(symbol=symbol, timeframe=timeframe, stop_loss_points=2.0, take_profit_points=4.0)
    context = BacktestContext(strategy_model=model, data=data, configuration=configuration, indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    session = BacktestRunner().try_execute(context)
    if not session.is_successful:
        st.sidebar.warning(f"'{name}': backtest failed validation, skipped.")
        return None

    return PortfolioStrategyEntry(strategy_model=model, backtest_result=session.result)


if st.sidebar.button("Build Portfolio", type="primary"):
    with st.spinner("Building and backtesting selected strategies..."):
        entries = [e for e in (_build_entry(name) for name in choices) if e is not None]

    if not entries:
        st.error("No selected strategy built and backtested successfully.")
        st.stop()

    manual_weights = tuple(
        ManualWeight(strategy_id=entry.strategy_model.metadata.id, weight=manual_weight_inputs.get(name, 1.0))
        for name, entry in zip(choices, entries)
    )
    configuration = PortfolioConfiguration(
        allocation_method=AllocationMethod(allocation_method_label),
        manual_weights=manual_weights,
        min_strategies_required=int(min_strategies_required),
        high_correlation_threshold=float(high_correlation_threshold),
    )
    engine = PortfolioManagementEngine()
    with st.spinner("Building portfolio..."):
        st.session_state.portfolio_session = engine.try_execute(tuple(entries), configuration)

if "portfolio_session" not in st.session_state:
    st.stop()

session = st.session_state.portfolio_session
st.subheader("Portfolio Result")
if not session.is_successful:
    st.error("Portfolio context failed validation:")
    st.code(session.validation.report())
    st.stop()

for warning in session.validation.warnings:
    st.info(str(warning))

result = session.result
report = PortfolioReport(result)

st.subheader("Executive Summary")
summary = report.executive_summary()
cols = st.columns(4)
cols[0].metric("Strategies combined", summary["total_strategies"])
cols[1].metric("Total net profit", f"{summary['total_net_profit']:.2f}")
cols[2].metric("Portfolio quality score", f"{summary['portfolio_quality_score']:.1f}")
cols[3].metric("Top strategy", summary["top_strategy_name"] or "-")
for finding in summary["key_findings"]:
    st.write(f"- {finding}")
st.caption(f"Checksum: {result.checksum}")

tabs = st.tabs(["Portfolio Report", "Allocation Report", "Risk Report", "Correlation & Exposure", "Ranking Report", "Analytics Report"])

with tabs[0]:
    st.json(report.portfolio_report())

with tabs[1]:
    st.markdown("**Per-Strategy Allocation**")
    st.dataframe(report.allocation_table(), use_container_width=True, hide_index=True)
    st.markdown("**Symbol Allocation**")
    st.dataframe(report.symbol_allocation_table(), use_container_width=True, hide_index=True)
    st.markdown("**Timeframe Allocation**")
    st.dataframe(report.timeframe_allocation_table(), use_container_width=True, hide_index=True)
    st.markdown("**Session Allocation**")
    st.dataframe(report.session_allocation_table(), use_container_width=True, hide_index=True)
    st.markdown("**Sector Allocation** (future-ready; empty until a sector source exists)")
    st.dataframe(report.sector_allocation_table(), use_container_width=True, hide_index=True)

with tabs[2]:
    st.json(report.risk_report())

with tabs[3]:
    st.markdown("**Correlation Matrix**")
    st.dataframe(report.correlation_table(), use_container_width=True, hide_index=True)
    st.markdown("**Symbol Exposure**")
    st.dataframe(report.exposure_table(), use_container_width=True, hide_index=True)

with tabs[4]:
    st.dataframe(report.ranking_table(), use_container_width=True, hide_index=True)

with tabs[5]:
    st.json(report.analytics_report())

with st.expander("Raw PortfolioResult (JSON)"):
    st.code(PortfolioSerializer().to_json(result), language="json")
