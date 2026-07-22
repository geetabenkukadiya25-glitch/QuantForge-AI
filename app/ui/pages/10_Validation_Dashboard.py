"""
Streamlit page: Validation Dashboard.

Build an executable strategy from SDL, run a small Optimization Engine
search to pick a candidate, then validate that candidate with Walk
Forward and Monte Carlo analysis. Phase 11 scope only -- this page (and
the module behind it) never optimizes, never backtests independently,
never connects to a broker, and never executes live trades.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar and a
bottom status bar. Its existing results tabs (Walk Forward / Monte Carlo
/ Robustness / Confidence) are unchanged. No engine, SDL, Optimization
Engine, or Validation Engine call changed -- every `st.sidebar.X(...)`
became `st.X(...)` inside a `with explorer_col:` block, and "Run
Optimization + Validation" moved into the toolbar as "Run".
"""

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
from app.job_manager import JobCategory, JobState, get_job_manager
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar
from app.ui.progress import VALIDATION_STEPS
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

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Validation Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Validation Dashboard")
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
job_manager = get_job_manager()

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


explorer_col, workspace_col, info_col = render_shell()

with info_col:
    st.subheader("Information")

with explorer_col:
    st.subheader("Explorer")
    st.header("1. Base Strategy")
    examples = _load_examples()
    choice = st.selectbox("SDL example", list(examples.keys()))

with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("val_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for the selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Compilation runs automatically for the selected strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Validation in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("stop") and _toolbar_job is not None:
        job_manager.cancel(_toolbar_job.id)
        notify("warning", f"Cancel requested: {_toolbar_job.name}")
        st.rerun()

    try:
        raw_data = parser.parse_file(examples[choice])
    except SDLParseError as exc:
        st.error(f"Could not parse example: {exc}")
        render_status_bar(module="Validation Dashboard", execution_status="Invalid Strategy", **job_manager.status_counts())
        st.stop()

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        st.error("This SDL document is invalid at the SDL layer (Phase 4):")
        st.code(sdl_result.report())
        render_status_bar(module="Validation Dashboard", execution_status="Invalid Strategy", **job_manager.status_counts())
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
        render_status_bar(module="Validation Dashboard", execution_status="Build Failed", **job_manager.status_counts())
        st.stop()

    base_model = build_result.model
    st.success(f"Built '{base_model.metadata.name}'")

with info_col:
    render_info_card("Strategy", [("Name", base_model.metadata.name), ("SDL file", f"{choice}.yaml")])

with explorer_col:
    st.header("2. Historical Data")
    uploaded_file = st.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

    st.header("3. Base Execution Assumptions")
    symbol = st.selectbox("Symbol", base_model.context_requirement.symbols)
    timeframe = st.selectbox("Timeframe", base_model.context_requirement.timeframes)
    stop_loss_points = st.number_input("Stop loss (points, 0 = none)", min_value=0.0, value=2.0, step=0.5)
    take_profit_points = st.number_input("Take profit (points, 0 = none)", min_value=0.0, value=4.0, step=0.5)

    st.header("4. Optimization (to pick a candidate)")
    max_candidates = st.number_input("Max candidates", min_value=1, value=10, step=1)
    objective_label = st.selectbox("Objective", [o.value for o in Objective if o != Objective.CUSTOM])

    st.header("5. Walk Forward")
    window_type_label = st.selectbox("Window type", [w.value for w in WindowType])
    in_sample_bars = st.number_input("In-sample bars", min_value=10, value=150, step=10)
    out_of_sample_bars = st.number_input("Out-of-sample bars", min_value=10, value=50, step=10)

    st.header("6. Monte Carlo")
    mc_method_label = st.selectbox("Method", [m.value for m in MonteCarloMethod])
    mc_iterations = st.number_input("Iterations", min_value=10, value=200, step=10)
    mc_seed = st.number_input("Random seed", min_value=0, value=42, step=1)

with info_col:
    render_info_card(
        "Configuration",
        [
            ("Symbol", symbol),
            ("Timeframe", timeframe),
            ("Window type", window_type_label),
            ("MC method", mc_method_label),
        ],
    )

with workspace_col:
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


with workspace_col:
    if uploaded_file is None:
        st.info("Upload historical OHLCV data in the Explorer to run optimization + validation.")
        render_status_bar(module="Validation Dashboard", strategy_status=base_model.metadata.name, execution_status="Awaiting Data", **job_manager.status_counts())
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        data = loader.load_csv(tmp_path, clean=True)
    except CSVFormatError as exc:
        st.error(f"Could not load historical data: {exc}")
        render_status_bar(module="Validation Dashboard", strategy_status=base_model.metadata.name, execution_status="Data Error", **job_manager.status_counts())
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

    base_configuration = BacktestConfiguration(
        symbol=symbol, timeframe=timeframe, stop_loss_points=stop_loss_points or None, take_profit_points=take_profit_points or None,
    )

    if toolbar_clicked.get("run"):
        def _run_validation(
            job,
            base_model=base_model, data=data, base_configuration=base_configuration, param_rows=param_rows,
            symbol=symbol, timeframe=timeframe, objective_label=objective_label, max_candidates=max_candidates,
            window_type_label=window_type_label, in_sample_bars=in_sample_bars, out_of_sample_bars=out_of_sample_bars,
            mc_method_label=mc_method_label, mc_iterations=mc_iterations, mc_seed=mc_seed,
            indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry,
        ):
            # `indicator_registry`/`smc_registry` are captured here (main
            # thread, at closure-definition time) since `st.session_state`
            # has no meaning inside the dispatcher thread this runs on.
            with job.progress.step(0):
                parameter_space = _build_parameter_space(param_rows)
                opt_configuration = OptimizationConfiguration(
                    strategy_id=base_model.metadata.id, symbol=symbol, timeframe=timeframe,
                    search_method=SearchMethod.GRID, objective=Objective(objective_label), max_candidates=int(max_candidates),
                )
                opt_engine = OptimizationEngine(
                    indicator_engine=IndicatorEngine(registry=indicator_registry),
                    smart_money_engine=SmartMoneyEngine(registry=smc_registry),
                )
            with job.progress.step(1):
                opt_session = opt_engine.try_execute(base_model, data, base_configuration, parameter_space, opt_configuration)

            val_session = None
            if opt_session.is_successful:
                with job.progress.step(2):
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
                        indicator_engine=IndicatorEngine(registry=indicator_registry),
                        smart_money_engine=SmartMoneyEngine(registry=smc_registry),
                    )
                    val_session = val_engine.try_execute(opt_session.result, base_model, base_configuration, data, val_configuration)
                with job.progress.step(3):
                    pass
            return (opt_session, val_session)

        job = job_manager.submit(
            name=f"Validation: {choice}",
            category=JobCategory.VALIDATION,
            operation=_run_validation,
            owner_page="Validation Dashboard",
            step_names=VALIDATION_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.val_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("val_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=base_model.metadata.name)
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Validation failed: {current_job.error}")
        render_status_bar(
            module="Validation Dashboard",
            strategy_status=base_model.metadata.name,
            execution_status=current_job.state.value if current_job else "Ready",
            job=current_job,
            **job_manager.status_counts(),
        )
        st.stop()

    opt_session, val_session = current_job.result
    st.subheader("Optimization Result")
    if not opt_session.is_successful:
        st.error("Optimization failed validation:")
        st.code(opt_session.validation.report())
        render_status_bar(module="Validation Dashboard", strategy_status=base_model.metadata.name, execution_status="Optimization Failed", **job_manager.status_counts())
        st.stop()
    st.success(f"Best candidate: {opt_session.result.best_candidate_id} (score {opt_session.result.statistics.best_score})")

    if val_session is None:
        render_status_bar(module="Validation Dashboard", strategy_status=base_model.metadata.name, execution_status="Ready", **job_manager.status_counts())
        st.stop()

    st.subheader("Validation Report")
    if val_session.is_successful:
        st.success(f"Valid ({len(val_session.validation.warnings)} warning(s))")
    else:
        st.error("Invalid:")
        st.code(val_session.validation.report())
        render_status_bar(module="Validation Dashboard", strategy_status=base_model.metadata.name, validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
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

    tabs = st.tabs(["Walk Forward Viewer", "Monte Carlo Viewer", "Robustness Viewer", "Confidence Viewer", "Export"])
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
    with tabs[4]:
        from app.validation_engine import ValidationSerializer

        export_json = ValidationSerializer().to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name=f"{choice}_validation_result.json", mime="application/json")

with info_col:
    render_info_card(
        "Execution Status",
        [
            ("Result", "Valid" if val_session.is_successful else "Invalid"),
            ("Robustness score", f"{summary['robustness_score']:.3f}" if summary["robustness_score"] is not None else "—"),
        ],
    )
    render_runtime_monitor(current_job.id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=base_model.metadata.name)

render_status_bar(
    module="Validation Dashboard",
    strategy_status=base_model.metadata.name,
    validation_status="Valid" if val_session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
