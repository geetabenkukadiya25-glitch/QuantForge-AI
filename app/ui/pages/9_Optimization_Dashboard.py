"""
Streamlit page: Optimization Dashboard.

Build an executable strategy from SDL, load historical OHLCV data, define
a parameter space, and run Grid Search or Random Search over it using the
existing Backtesting Engine. Phase 10 scope only -- this page (and the
module behind it) never executes live trades, connects to a broker, or
modifies Strategy Builder logic.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.optimization_engine import (
    Objective,
    OptimizationConfiguration,
    OptimizationEngine,
    OptimizationReport,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.progress import OPTIMIZATION_STEPS, ProgressTracker, tracked_step

st.set_page_config(page_title="Optimization Dashboard - QuantForge AI", page_icon="🧪", layout="wide")

st.title("Optimization Dashboard")
st.caption(
    "Searches StrategyModel parameters using the existing Backtesting Engine. "
    "This module never executes live trades, connects to a broker, or modifies Strategy Builder logic."
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


st.sidebar.header("1. Base Strategy")
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

base_model = build_result.model
st.sidebar.success(f"Built '{base_model.metadata.name}'")

st.sidebar.header("2. Historical Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

st.sidebar.header("3. Base Execution Assumptions")
symbol = st.sidebar.selectbox("Symbol", base_model.context_requirement.symbols)
timeframe = st.sidebar.selectbox("Timeframe", base_model.context_requirement.timeframes)
stop_loss_points = st.sidebar.number_input("Stop loss (points, 0 = none)", min_value=0.0, value=2.0, step=0.5)
take_profit_points = st.sidebar.number_input("Take profit (points, 0 = none)", min_value=0.0, value=4.0, step=0.5)
commission_per_lot = st.sidebar.number_input("Commission per lot", min_value=0.0, value=0.0, step=0.5)

st.sidebar.header("4. Search Settings")
search_method_label = st.sidebar.selectbox("Search method", ["GRID", "RANDOM"])
objective_label = st.sidebar.selectbox("Objective", [o.value for o in Objective if o != Objective.CUSTOM])
max_candidates = st.sidebar.number_input("Max candidates (required for RANDOM)", min_value=1, value=20, step=1)
random_seed = st.sidebar.number_input("Random seed", min_value=0, value=42, step=1)
top_n = st.sidebar.number_input("Top N candidates to show", min_value=1, value=5, step=1)

st.subheader("Parameter Space Viewer")
st.caption(
    "Each row varies one dimension. Target 'component.<local_name>.<param>' varies an "
    "indicator/detector's parameter; 'configuration.<field>' varies a BacktestConfiguration field."
)
component_names = [ref.local_name for ref in base_model.indicators] + [ref.local_name for ref in base_model.detectors]
st.caption(f"Available components on this strategy: {', '.join(component_names) or '(none)'}")

default_rows = pd.DataFrame(
    [
        {"name": "component.fast_ma.window", "target": "COMPONENT", "kind": "INTEGER", "min_value": 5.0, "max_value": 15.0, "step": 5.0, "choices": "", "fixed_value": ""},
    ]
)
param_rows = st.data_editor(
    default_rows,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "target": st.column_config.SelectboxColumn(options=["COMPONENT", "CONFIGURATION"]),
        "kind": st.column_config.SelectboxColumn(options=["INTEGER", "FLOAT", "BOOLEAN", "ENUM", "FIXED"]),
    },
)


def _build_parameter_space(rows: pd.DataFrame) -> ParameterSpace:
    definitions = []
    for _, row in rows.iterrows():
        if not row.get("name"):
            continue
        choices_json = json.dumps([c.strip() for c in str(row.get("choices") or "").split(",") if c.strip()])
        fixed_raw = row.get("fixed_value")
        fixed_json = json.dumps(fixed_raw) if fixed_raw not in (None, "") else None
        definitions.append(
            ParameterDefinition(
                name=row["name"],
                target=ParameterTarget(row["target"]),
                kind=ParameterKind(row["kind"]),
                min_value=row.get("min_value") if pd.notna(row.get("min_value")) else None,
                max_value=row.get("max_value") if pd.notna(row.get("max_value")) else None,
                step=row.get("step") if pd.notna(row.get("step")) else None,
                choices_json=choices_json,
                fixed_value_json=fixed_json,
            )
        )
    return ParameterSpace(definitions=tuple(definitions))


if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to run an optimization.")
    st.stop()

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

base_configuration = BacktestConfiguration(
    symbol=symbol,
    timeframe=timeframe,
    stop_loss_points=stop_loss_points or None,
    take_profit_points=take_profit_points or None,
    commission_per_lot=commission_per_lot,
)

optimization_configuration = OptimizationConfiguration(
    strategy_id=base_model.metadata.id,
    symbol=symbol,
    timeframe=timeframe,
    search_method=SearchMethod(search_method_label),
    objective=Objective(objective_label),
    max_candidates=int(max_candidates),
    random_seed=int(random_seed),
    top_n=int(top_n),
)

engine = OptimizationEngine(
    indicator_engine=IndicatorEngine(registry=st.session_state.indicator_registry),
    smart_money_engine=SmartMoneyEngine(registry=st.session_state.smc_registry),
)

if st.sidebar.button("Run Optimization", type="primary"):
    progress_placeholder = st.sidebar.empty()
    tracker = ProgressTracker(OPTIMIZATION_STEPS)
    with tracked_step(tracker, 0, progress_placeholder):
        parameter_space = _build_parameter_space(param_rows)
    with tracked_step(tracker, 1, progress_placeholder):
        st.session_state.optimization_session = engine.try_execute(
            base_model, data, base_configuration, parameter_space, optimization_configuration
        )
    with tracked_step(tracker, 2, progress_placeholder):
        pass

if "optimization_session" not in st.session_state:
    st.stop()

session = st.session_state.optimization_session

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
report = OptimizationReport(result)

st.subheader("Optimization Results")
stats = result.statistics
cols = st.columns(5)
cols[0].metric("Total candidates", stats.total_candidates)
cols[1].metric("Evaluated", stats.evaluated_candidates)
cols[2].metric("Failed", stats.failed_candidates)
cols[3].metric("Best score", f"{stats.best_score:.4f}" if stats.best_score is not None else "—")
cols[4].metric("Mean score", f"{stats.mean_score:.4f}" if stats.mean_score is not None else "—")
st.caption(f"Objective: {stats.objective.value} · Checksum: {result.checksum}")

st.subheader("Best Candidate")
best = report.best_candidate()
if best is None:
    st.warning("No candidate succeeded.")
else:
    st.write(f"**{best.candidate_id}** — score {best.score:.4f}")
    st.code(best.parameters_json, language="json")
    if best.statistics:
        bcols = st.columns(4)
        bcols[0].metric("Net profit", f"{best.statistics.net_profit:,.2f}")
        bcols[1].metric("Win rate", f"{best.statistics.win_rate:.1f}%")
        bcols[2].metric("Max drawdown", f"{best.statistics.max_drawdown:,.2f}")
        bcols[3].metric("Sharpe (framework)", f"{best.statistics.sharpe_ratio:.2f}" if best.statistics.sharpe_ratio is not None else "—")

st.subheader("Candidate Explorer")
st.dataframe(report.history_dataframe(), use_container_width=True, hide_index=True)

st.subheader("Performance Comparison")
st.dataframe(report.performance_comparison_dataframe(), use_container_width=True, hide_index=True)

st.subheader("Parameter Ranking")
st.dataframe(report.parameter_ranking(), use_container_width=True, hide_index=True)

with st.expander("Raw OptimizationResult (JSON)"):
    from app.optimization_engine import OptimizationSerializer

    st.code(OptimizationSerializer().to_json(result), language="json")
