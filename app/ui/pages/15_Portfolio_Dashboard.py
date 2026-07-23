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

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No engine, SDL, or
Portfolio Management Engine call changed -- every `st.sidebar.X(...)`
became `st.X(...)` inside a `with explorer_col:` block, and "Build
Portfolio" moved into the toolbar as "Run".
"""

from pathlib import Path

import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
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
from app.ui.components import ToolbarAction, notify, render_command_bar, render_dataset_picker, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar

PORTFOLIO_STEPS = ["Building & Backtesting Strategies", "Building Portfolio"]

st.set_page_config(page_title="Portfolio Dashboard - QuantForge AI", page_icon="📊", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Portfolio Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Portfolio Dashboard")
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
job_manager = get_job_manager()
indicator_engine = IndicatorEngine(registry=st.session_state.indicator_registry)
smart_money_engine = SmartMoneyEngine(registry=st.session_state.smc_registry)

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


explorer_col, workspace_col, info_col = render_shell()

with info_col:
    st.subheader("Information")

with explorer_col:
    st.subheader("Explorer")
    st.header("1. Strategies in the Portfolio")
    examples = _load_examples()
    choices = st.multiselect("SDL examples", list(examples.keys()), default=list(examples.keys())[:2])

    st.header("2. Historical Data")
    data, dataset_record = render_dataset_picker(page_key="portfolio")

    st.header("3. Allocation")
    allocation_method_label = st.selectbox("Allocation method", [m.value for m in AllocationMethod])
    manual_weight_inputs: dict[str, float] = {}
    if allocation_method_label == AllocationMethod.MANUAL_WEIGHT.value:
        st.caption("Manual weight per strategy (normalized automatically).")
        for name in choices:
            manual_weight_inputs[name] = st.number_input(f"Weight: {name}", min_value=0.0, value=1.0, step=0.1, key=f"weight_{name}")

    st.header("4. Thresholds")
    high_correlation_threshold = st.slider("High correlation threshold", min_value=-1.0, max_value=1.0, value=0.7, step=0.05)
    min_strategies_required = st.number_input("Min strategies required", min_value=1, value=2, step=1)

with info_col:
    render_info_card(
        "Configuration",
        [
            ("Strategies selected", len(choices)),
            ("Allocation method", allocation_method_label),
            ("Min strategies required", int(min_strategies_required)),
        ],
    )

with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("portfolio_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for each selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Compilation runs automatically for each selected strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Portfolio in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("stop") and _toolbar_job is not None:
        job_manager.cancel(_toolbar_job.id)
        notify("warning", f"Cancel requested: {_toolbar_job.name}")
        st.rerun()

    if not choices:
        st.info("Select at least one SDL example in the Explorer.")
        render_status_bar(module="Portfolio Dashboard", execution_status="Awaiting Selection", **job_manager.status_counts())
        st.stop()
    if data is None:
        st.info("Select or upload historical OHLCV data in the Explorer to build and backtest the selected strategies.")
        render_status_bar(module="Portfolio Dashboard", execution_status="Awaiting Data", **job_manager.status_counts())
        st.stop()

    st.success(f"Loaded {len(data)} candle(s).")

    def _build_entry(name: str, warnings: list[str], indicator_registry, smc_registry) -> PortfolioStrategyEntry | None:
        # Runs inside the Job Manager's dispatcher thread -- never calls
        # `st.*` directly (including `st.session_state`, which has no
        # meaning off the main script thread); the registries are passed
        # in as plain objects, captured in the main thread before
        # submission. Skip reasons are collected into `warnings` and
        # displayed by the main script thread once the job completes.
        try:
            raw_data = parser.parse_file(examples[name])
        except SDLParseError as exc:
            warnings.append(f"'{name}': could not parse ({exc}).")
            return None

        sdl_result = SDLValidator().validate(raw_data)
        if not sdl_result.is_valid:
            warnings.append(f"'{name}': failed SDL validation, skipped.")
            return None

        strategy_context = StrategyContext(sdl_definition=sdl_result.definition, indicator_registry=indicator_registry, smc_registry=smc_registry)
        build_result = strategy_builder.try_build(strategy_context)
        if not build_result.is_valid:
            warnings.append(f"'{name}': failed Strategy Builder validation, skipped.")
            return None

        model = build_result.model
        symbol = model.context_requirement.symbols[0]
        timeframe = model.context_requirement.timeframes[0]
        configuration = BacktestConfiguration(symbol=symbol, timeframe=timeframe, stop_loss_points=2.0, take_profit_points=4.0)
        context = BacktestContext(strategy_model=model, data=data, configuration=configuration, indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
        session = BacktestRunner().try_execute(context)
        if not session.is_successful:
            warnings.append(f"'{name}': backtest failed validation, skipped.")
            return None

        return PortfolioStrategyEntry(strategy_model=model, backtest_result=session.result)

    if toolbar_clicked.get("run"):
        def _run_portfolio(
            job, choices=choices, allocation_method_label=allocation_method_label, manual_weight_inputs=manual_weight_inputs,
            min_strategies_required=min_strategies_required, high_correlation_threshold=high_correlation_threshold,
            indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry,
        ):
            skip_warnings: list[str] = []
            with job.progress.step(0):
                entries = [e for e in (_build_entry(name, skip_warnings, indicator_registry, smc_registry) for name in choices) if e is not None]

            if not entries:
                return (None, skip_warnings)

            with job.progress.step(1):
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
                session = engine.try_execute(tuple(entries), configuration)
            return (session, skip_warnings)

        job = job_manager.submit(
            name=f"Portfolio: {len(choices)} strategy(ies)",
            category=JobCategory.PORTFOLIO,
            operation=_run_portfolio,
            owner_page="Portfolio Dashboard",
            step_names=PORTFOLIO_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.portfolio_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("portfolio_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, dataset_label=dataset_record.filename if dataset_record else None, strategy_label=f"{len(choices)} strategy(ies)")
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Portfolio build failed: {current_job.error}")
        render_status_bar(module="Portfolio Dashboard", execution_status=current_job.state.value if current_job else "Ready", job=current_job, **job_manager.status_counts())
        st.stop()

    session, skip_warnings = current_job.result
    for skip_warning in skip_warnings:
        st.warning(skip_warning)

    if session is None:
        st.error("No selected strategy built and backtested successfully.")
        render_status_bar(module="Portfolio Dashboard", execution_status="No Results", **job_manager.status_counts())
        st.stop()

    st.subheader("Portfolio Result")
    if not session.is_successful:
        st.error("Portfolio context failed validation:")
        st.code(session.validation.report())
        render_status_bar(module="Portfolio Dashboard", validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
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

    tabs = st.tabs(["Portfolio Report", "Allocation Report", "Risk Report", "Correlation & Exposure", "Ranking Report", "Analytics Report", "Export"])

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

    with tabs[6]:
        export_json = PortfolioSerializer().to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name="portfolio_result.json", mime="application/json")

with info_col:
    render_info_card(
        "Execution Status",
        [
            ("Result", "Success" if session.is_successful else "Failed"),
            ("Strategies combined", summary["total_strategies"]),
            ("Portfolio quality score", f"{summary['portfolio_quality_score']:.1f}"),
        ],
    )
    render_runtime_monitor(current_job.id, dataset_label=dataset_record.filename if dataset_record else None, strategy_label=f"{len(choices)} strategy(ies)")

render_status_bar(
    module="Portfolio Dashboard",
    validation_status="Valid" if session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
