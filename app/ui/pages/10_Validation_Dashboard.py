"""
Streamlit page: Validation Dashboard.

Build an executable strategy from SDL, run a small Optimization Engine
search to pick a candidate, then validate that candidate with Walk
Forward and Monte Carlo analysis. Phase 11 scope only -- this page (and
the module behind it) never optimizes, never backtests independently,
never connects to a broker, and never executes live trades.
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
from app.validation_engine import (
    MonteCarloConfiguration,
    MonteCarloMethod,
    ValidationConfiguration,
    ValidationEngine,
    ValidationReport,
    WalkForwardConfiguration,
    WindowType,
)

st.set_page_config(page_title="Validation Dashboard - QuantForge AI", page_icon="🔬", layout="wide")

st.title("Validation Dashboard")
st.caption(
    "Walk Forward and Monte Carlo validation of an already-chosen Optimization Engine candidate. "
    "This module never optimizes, never backtests independently, never connects to a broker, and never trades live."
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

st.sidebar.header("4. Optimization (to pick a candidate)")
max_candidates = st.sidebar.number_input("Max candidates", min_value=1, value=10, step=1)
objective_label = st.sidebar.selectbox("Objective", [o.value for o in Objective if o != Objective.CUSTOM])

st.sidebar.header("5. Walk Forward")
window_type_label = st.sidebar.selectbox("Window type", [w.value for w in WindowType])
in_sample_bars = st.sidebar.number_input("In-sample bars", min_value=10, value=150, step=10)
out_of_sample_bars = st.sidebar.number_input("Out-of-sample bars", min_value=10, value=50, step=10)

st.sidebar.header("6. Monte Carlo")
mc_method_label = st.sidebar.selectbox("Method", [m.value for m in MonteCarloMethod])
mc_iterations = st.sidebar.number_input("Iterations", min_value=10, value=200, step=10)
mc_seed = st.sidebar.number_input("Random seed", min_value=0, value=42, step=1)

st.subheader("Parameter Space (for the Optimization step)")
component_names = [ref.local_name for ref in base_model.indicators] + [ref.local_name for ref in base_model.detectors]
st.caption(f"Available components on this strategy: {', '.join(component_names) or '(none)'}")
default_rows = pd.DataFrame(
    [{"name": "component.fast_ma.window", "target": "COMPONENT", "kind": "INTEGER", "min_value": 5.0, "max_value": 15.0, "step": 5.0}]
)
param_rows = st.data_editor(
    default_rows, num_rows="dynamic", use_container_width=True,
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
        definitions.append(
            ParameterDefinition(
                name=row["name"], target=ParameterTarget(row["target"]), kind=ParameterKind(row["kind"]),
                min_value=row.get("min_value") if pd.notna(row.get("min_value")) else None,
                max_value=row.get("max_value") if pd.notna(row.get("max_value")) else None,
                step=row.get("step") if pd.notna(row.get("step")) else None,
            )
        )
    return ParameterSpace(definitions=tuple(definitions))


if uploaded_file is None:
    st.info("Upload historical OHLCV data in the sidebar to run optimization + validation.")
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = Path(tmp.name)

try:
    data = loader.load_csv(tmp_path, clean=True)
except CSVFormatError as exc:
    st.error(f"Could not load historical data: {exc}")
    st.stop()

base_configuration = BacktestConfiguration(
    symbol=symbol, timeframe=timeframe, stop_loss_points=stop_loss_points or None, take_profit_points=take_profit_points or None,
)

if st.sidebar.button("Run Optimization + Validation", type="primary"):
    parameter_space = _build_parameter_space(param_rows)
    opt_configuration = OptimizationConfiguration(
        strategy_id=base_model.metadata.id, symbol=symbol, timeframe=timeframe,
        search_method=SearchMethod.GRID, objective=Objective(objective_label), max_candidates=int(max_candidates),
    )
    opt_engine = OptimizationEngine(
        indicator_engine=IndicatorEngine(registry=st.session_state.indicator_registry),
        smart_money_engine=SmartMoneyEngine(registry=st.session_state.smc_registry),
    )
    with st.spinner("Running optimization..."):
        opt_session = opt_engine.try_execute(base_model, data, base_configuration, parameter_space, opt_configuration)
    st.session_state.opt_session = opt_session

    if opt_session.is_successful:
        wf_configuration = WalkForwardConfiguration(
            window_type=WindowType(window_type_label), in_sample_bars=int(in_sample_bars), out_of_sample_bars=int(out_of_sample_bars),
            objective=Objective(objective_label),
        )
        mc_configuration = MonteCarloConfiguration(method=MonteCarloMethod(mc_method_label), iterations=int(mc_iterations), random_seed=int(mc_seed))
        val_configuration = ValidationConfiguration(
            strategy_id=base_model.metadata.id, symbol=symbol, timeframe=timeframe,
            run_walk_forward=True, run_monte_carlo=True, walk_forward=wf_configuration, monte_carlo=mc_configuration,
        )
        val_engine = ValidationEngine(
            indicator_engine=IndicatorEngine(registry=st.session_state.indicator_registry),
            smart_money_engine=SmartMoneyEngine(registry=st.session_state.smc_registry),
        )
        with st.spinner("Running walk-forward and Monte Carlo validation..."):
            st.session_state.val_session = val_engine.try_execute(opt_session.result, base_model, base_configuration, data, val_configuration)

if "opt_session" not in st.session_state:
    st.stop()

opt_session = st.session_state.opt_session
st.subheader("Optimization Result")
if not opt_session.is_successful:
    st.error("Optimization failed validation:")
    st.code(opt_session.validation.report())
    st.stop()
st.success(f"Best candidate: {opt_session.result.best_candidate_id} (score {opt_session.result.statistics.best_score})")

if "val_session" not in st.session_state:
    st.stop()

val_session = st.session_state.val_session
st.subheader("Validation Report")
if val_session.is_successful:
    st.success(f"Valid ({len(val_session.validation.warnings)} warning(s))")
else:
    st.error("Invalid:")
    st.code(val_session.validation.report())
    st.stop()

result = val_session.result
report = ValidationReport(result)

st.subheader("Validation Summary")
summary = report.validation_summary()
cols = st.columns(4)
cols[0].metric("Walk-forward pass rate", f"{summary['walk_forward_pass_rate']:.1%}" if summary["walk_forward_pass_rate"] is not None else "—")
cols[1].metric("MC probability of profit", f"{summary['monte_carlo_probability_of_profit']:.1%}" if summary["monte_carlo_probability_of_profit"] is not None else "—")
cols[2].metric("Robustness score", f"{summary['robustness_score']:.3f}" if summary["robustness_score"] is not None else "—")
cols[3].metric("Stability score", f"{summary['stability_score']:.3f}" if summary["stability_score"] is not None else "—")
st.caption(f"Checksum: {result.checksum}")

tabs = st.tabs(["Walk Forward Viewer", "Monte Carlo Viewer", "Robustness Viewer", "Confidence Viewer"])
with tabs[0]:
    st.dataframe(report.walk_forward_report(), use_container_width=True, hide_index=True)
with tabs[1]:
    st.dataframe(report.monte_carlo_report(), use_container_width=True, hide_index=True)
    if result.monte_carlo_result:
        st.bar_chart(pd.DataFrame({"net_profit": [p.net_profit for p in result.monte_carlo_result.distribution]}))
with tabs[2]:
    st.json(report.robustness_report())
with tabs[3]:
    st.json(report.confidence_report())

with st.expander("Raw ValidationResult (JSON)"):
    from app.validation_engine import ValidationSerializer

    st.code(ValidationSerializer().to_json(result), language="json")
