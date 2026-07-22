"""
Streamlit page: Optimization Dashboard.

Build an executable strategy from SDL, load historical OHLCV data, define
a parameter space, and run Grid Search or Random Search over it using the
existing Backtesting Engine. Phase 10 scope only -- this page (and the
module behind it) never executes live trades, connects to a broker, or
modifies Strategy Builder logic.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No engine, SDL, or
Optimization Engine call changed -- every `st.sidebar.X(...)` became
`st.X(...)` inside a `with explorer_col:` block, and "Run Optimization"
moved into the toolbar as "Run".
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
from app.job_manager import JobCategory, JobState, get_job_manager
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar
from app.ui.progress import OPTIMIZATION_STEPS

st.set_page_config(page_title="Optimization Dashboard - QuantForge AI", page_icon="🧪", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Optimization Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Optimization Dashboard")
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
    _toolbar_job = job_manager.get(st.session_state.get("opt_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for the selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Compilation runs automatically for the selected strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Optimization in this phase."),
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
        render_status_bar(module="Optimization Dashboard", execution_status="Invalid Strategy", **job_manager.status_counts())
        st.stop()

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        st.error("This SDL document is invalid at the SDL layer (Phase 4):")
        st.code(sdl_result.report())
        render_status_bar(module="Optimization Dashboard", execution_status="Invalid Strategy", **job_manager.status_counts())
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
        render_status_bar(module="Optimization Dashboard", execution_status="Build Failed", **job_manager.status_counts())
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
    commission_per_lot = st.number_input("Commission per lot", min_value=0.0, value=0.0, step=0.5)

    st.header("4. Search Settings")
    search_method_label = st.selectbox("Search method", ["GRID", "RANDOM"])
    objective_label = st.selectbox("Objective", [o.value for o in Objective if o != Objective.CUSTOM])
    max_candidates = st.number_input("Max candidates (required for RANDOM)", min_value=1, value=20, step=1)
    random_seed = st.number_input("Random seed", min_value=0, value=42, step=1)
    top_n = st.number_input("Top N candidates to show", min_value=1, value=5, step=1)

with info_col:
    render_info_card(
        "Configuration",
        [
            ("Symbol", symbol),
            ("Timeframe", timeframe),
            ("Search method", search_method_label),
            ("Objective", objective_label),
        ],
    )

with workspace_col:
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


with workspace_col:
    if uploaded_file is None:
        st.info("Upload historical OHLCV data in the Explorer to run an optimization.")
        render_status_bar(module="Optimization Dashboard", strategy_status=base_model.metadata.name, execution_status="Awaiting Data", **job_manager.status_counts())
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        data = loader.load_csv(tmp_path, clean=True)
    except CSVFormatError as exc:
        st.error(f"Could not load historical data: {exc}")
        render_status_bar(module="Optimization Dashboard", strategy_status=base_model.metadata.name, execution_status="Data Error", **job_manager.status_counts())
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

    if toolbar_clicked.get("run"):
        def _run_optimization(job, base_model=base_model, data=data, base_configuration=base_configuration, optimization_configuration=optimization_configuration, engine=engine, param_rows=param_rows):
            with job.progress.step(0):
                parameter_space = _build_parameter_space(param_rows)
            with job.progress.step(1):
                result = engine.try_execute(base_model, data, base_configuration, parameter_space, optimization_configuration)
            with job.progress.step(2):
                pass
            return result

        job = job_manager.submit(
            name=f"Optimization: {choice}",
            category=JobCategory.OPTIMIZATION,
            operation=_run_optimization,
            owner_page="Optimization Dashboard",
            step_names=OPTIMIZATION_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.opt_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("opt_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=base_model.metadata.name)
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Optimization failed: {current_job.error}")
        render_status_bar(
            module="Optimization Dashboard",
            strategy_status=base_model.metadata.name,
            execution_status=current_job.state.value if current_job else "Ready",
            job=current_job,
            **job_manager.status_counts(),
        )
        st.stop()

    session = current_job.result

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
        render_status_bar(module="Optimization Dashboard", strategy_status=base_model.metadata.name, validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
        st.stop()

    result = session.result
    report = OptimizationReport(result)

    overview_tab, candidates_tab, ranking_tab, export_tab = st.tabs(["Overview", "Candidates", "Parameter Ranking", "Export"])

    with overview_tab:
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

    with candidates_tab:
        st.subheader("Candidate Explorer")
        st.dataframe(report.history_dataframe(), use_container_width=True, hide_index=True)

        st.subheader("Performance Comparison")
        st.dataframe(report.performance_comparison_dataframe(), use_container_width=True, hide_index=True)

    with ranking_tab:
        st.subheader("Parameter Ranking")
        st.dataframe(report.parameter_ranking(), use_container_width=True, hide_index=True)

    with export_tab:
        from app.optimization_engine import OptimizationSerializer

        export_json = OptimizationSerializer().to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name=f"{choice}_optimization_result.json", mime="application/json")

with info_col:
    render_info_card(
        "Execution Status",
        [
            ("Result", "Success" if session.is_successful else "Failed"),
            ("Evaluated candidates", stats.evaluated_candidates),
            ("Best score", f"{stats.best_score:.4f}" if stats.best_score is not None else "—"),
        ],
    )
    render_runtime_monitor(current_job.id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=base_model.metadata.name)

render_status_bar(
    module="Optimization Dashboard",
    strategy_status=base_model.metadata.name,
    validation_status="Valid" if session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
