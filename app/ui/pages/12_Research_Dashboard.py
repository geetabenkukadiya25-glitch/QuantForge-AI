"""
Streamlit page: Research Dashboard.

Compares and ranks multiple already-backtested strategies, generating
professional statistics, scores, advanced analytics, insights, and
recommendations. This page (and the module behind it) is NOT an AI
model -- it never executes a trade, never optimizes a strategy, never
replays a chart, and never connects to a broker or MT5. It consumes ONLY
already-completed Strategy Builder / Backtesting Engine / (optionally)
Optimization Engine / Validation Engine outputs.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.research_engine import RankingMetric, ResearchConfiguration, ResearchEngine, ResearchReport, ResearchSerializer, StrategyRecord
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.progress import ProgressTracker, RESEARCH_STEPS, tracked_step

st.set_page_config(page_title="Research Dashboard - QuantForge AI", page_icon="🧠", layout="wide")

st.title("Research Dashboard")
st.caption(
    "Institutional research over already-completed strategy results: comparison, ranking, statistics, "
    "and recommendations. This module is NOT an AI model. It never trades, optimizes, or replays charts."
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


st.sidebar.header("1. Strategies to Compare")
examples = _load_examples()
choices = st.sidebar.multiselect("SDL examples", list(examples.keys()), default=list(examples.keys())[:2])

st.sidebar.header("2. Historical Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

st.sidebar.header("3. Ranking")
ranking_metric_label = st.sidebar.selectbox("Rank by", [m.value for m in RankingMetric])
min_trades = st.sidebar.number_input("Min trades for confidence", min_value=1, value=30, step=1)
max_drawdown_pct = st.sidebar.number_input("Max acceptable drawdown %", min_value=1.0, value=30.0, step=1.0)
institutional_min_score = st.sidebar.number_input("Institutional-grade minimum score", min_value=0.0, max_value=100.0, value=70.0, step=1.0)

if not choices:
    st.info("Select at least one SDL example in the sidebar.")
    st.stop()
if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to build and backtest the selected strategies.")
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


def _build_record(name: str) -> StrategyRecord | None:
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

    return StrategyRecord(strategy_model=model, backtest_result=session.result)


if st.sidebar.button("Run Research", type="primary"):
    progress_placeholder = st.sidebar.empty()
    tracker = ProgressTracker(RESEARCH_STEPS)
    with tracked_step(tracker, 0, progress_placeholder):
        records = [r for r in (_build_record(name) for name in choices) if r is not None]

    if not records:
        st.error("No selected strategy built and backtested successfully.")
        st.stop()

    with tracked_step(tracker, 1, progress_placeholder):
        configuration = ResearchConfiguration(
            ranking_metric=RankingMetric(ranking_metric_label),
            min_trades_for_confidence=int(min_trades),
            max_acceptable_drawdown_pct=float(max_drawdown_pct),
            institutional_min_score=float(institutional_min_score),
        )
        engine = ResearchEngine()
        st.session_state.research_session = engine.try_execute(tuple(records), configuration)

    with tracked_step(tracker, 2, progress_placeholder):
        pass

if "research_session" not in st.session_state:
    st.stop()

session = st.session_state.research_session
st.subheader("Research Result")
if not session.is_successful:
    st.error("Research context failed validation:")
    st.code(session.validation.report())
    st.stop()

for warning in session.validation.warnings:
    st.info(str(warning))

result = session.result
report = ResearchReport(result)

st.subheader("Executive Summary")
summary = report.executive_summary()
cols = st.columns(4)
cols[0].metric("Strategies analyzed", summary["total_strategies_analyzed"])
cols[1].metric("Top strategy", summary["top_strategy_name"] or "-")
cols[2].metric("Avg institutional score", f"{summary['average_institutional_quality_score']:.1f}")
cols[3].metric("Institutional-grade count", summary["institutional_grade_count"])
for finding in summary["key_findings"]:
    st.write(f"- {finding}")
st.caption(f"Checksum: {result.checksum}")

tabs = st.tabs(["Rankings", "Comparison Table", "Statistics Charts", "Advanced Analytics", "Insights", "Recommendations"])

with tabs[0]:
    st.dataframe(report.rankings_table(), use_container_width=True, hide_index=True)

with tabs[1]:
    st.dataframe(report.comparison_table(), use_container_width=True, hide_index=True)

with tabs[2]:
    rankings_df = report.rankings_table()
    if not rankings_df.empty:
        st.bar_chart(rankings_df.set_index("strategy_name")[["net_profit"]])
        st.bar_chart(rankings_df.set_index("strategy_name")[["institutional_quality_score", "confidence_score", "strategy_score"]])

with tabs[3]:
    st.markdown("**Indicator Usage**")
    st.dataframe(report.indicator_usage_table(), use_container_width=True, hide_index=True)
    st.markdown("**Smart Money Detector Usage**")
    st.dataframe(report.smart_money_usage_table(), use_container_width=True, hide_index=True)
    st.markdown("**Symbol Performance**")
    st.dataframe(report.symbol_performance_table(), use_container_width=True, hide_index=True)
    st.markdown("**Timeframe Performance**")
    st.dataframe(report.timeframe_performance_table(), use_container_width=True, hide_index=True)
    st.markdown("**Session Performance**")
    st.dataframe(report.session_performance_table(), use_container_width=True, hide_index=True)

with tabs[4]:
    strategy_id = st.selectbox("Strategy", [r.strategy_id for r in result.rankings])
    insights = report.insights_for(strategy_id)
    col1, col2, col3 = st.columns(3)
    col1.markdown("**Strengths**")
    for s in insights.get("strengths", []):
        col1.write(f"- {s}")
    col2.markdown("**Weaknesses**")
    for w in insights.get("weaknesses", []):
        col2.write(f"- {w}")
    col3.markdown("**Warnings**")
    for w in insights.get("warnings", []):
        col3.write(f"- {w}")

with tabs[5]:
    st.dataframe(report.recommendations_table(), use_container_width=True, hide_index=True)

with st.expander("Raw ResearchResult (JSON)"):
    st.code(ResearchSerializer().to_json(result), language="json")
