"""
Streamlit page: Research Dashboard.

Compares and ranks multiple already-backtested strategies, generating
professional statistics, scores, advanced analytics, insights, and
recommendations. This page (and the module behind it) is NOT an AI
model -- it never executes a trade, never optimizes a strategy, never
replays a chart, and never connects to a broker or MT5. It consumes ONLY
already-completed Strategy Builder / Backtesting Engine / (optionally)
Optimization Engine / Validation Engine outputs.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No engine, SDL, or Research
Engine call changed -- every `st.sidebar.X(...)` became `st.X(...)`
inside a `with explorer_col:` block, and "Run Research" moved into the
toolbar as "Run".
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestContext, BacktestRunner
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
from app.research_engine import RankingMetric, ResearchConfiguration, ResearchEngine, ResearchReport, ResearchSerializer, StrategyRecord
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar
from app.ui.progress import RESEARCH_STEPS

st.set_page_config(page_title="Research Dashboard - QuantForge AI", page_icon="🧠", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Research Dashboard")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Research Dashboard")
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
    st.header("1. Strategies to Compare")
    examples = _load_examples()
    choices = st.multiselect("SDL examples", list(examples.keys()), default=list(examples.keys())[:2])

    st.header("2. Historical Data")
    uploaded_file = st.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])

    st.header("3. Ranking")
    ranking_metric_label = st.selectbox("Rank by", [m.value for m in RankingMetric])
    min_trades = st.number_input("Min trades for confidence", min_value=1, value=30, step=1)
    max_drawdown_pct = st.number_input("Max acceptable drawdown %", min_value=1.0, value=30.0, step=1.0)
    institutional_min_score = st.number_input("Institutional-grade minimum score", min_value=0.0, max_value=100.0, value=70.0, step=1.0)

with info_col:
    render_info_card(
        "Configuration",
        [
            ("Strategies selected", len(choices)),
            ("Rank by", ranking_metric_label),
            ("Min trades", int(min_trades)),
        ],
    )

with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("research_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for each selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Compilation runs automatically for each selected strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Research in this phase."),
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
        render_status_bar(module="Research Dashboard", execution_status="Awaiting Selection", **job_manager.status_counts())
        st.stop()
    if uploaded_file is None:
        st.info("Upload historical OHLCV data in the Explorer to build and backtest the selected strategies.")
        render_status_bar(module="Research Dashboard", execution_status="Awaiting Data", **job_manager.status_counts())
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        data = loader.load_csv(tmp_path, clean=True)
    except CSVFormatError as exc:
        st.error(f"Could not load historical data: {exc}")
        render_status_bar(module="Research Dashboard", execution_status="Data Error", **job_manager.status_counts())
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

    st.success(f"Loaded {len(data)} candle(s).")

    def _build_record(name: str, warnings: list[str], indicator_registry, smc_registry) -> StrategyRecord | None:
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

        return StrategyRecord(strategy_model=model, backtest_result=session.result)

    if toolbar_clicked.get("run"):
        def _run_research(
            job, choices=choices, ranking_metric_label=ranking_metric_label, min_trades=min_trades,
            max_drawdown_pct=max_drawdown_pct, institutional_min_score=institutional_min_score,
            indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry,
        ):
            skip_warnings: list[str] = []
            with job.progress.step(0):
                records = [r for r in (_build_record(name, skip_warnings, indicator_registry, smc_registry) for name in choices) if r is not None]

            if not records:
                return (None, skip_warnings)

            with job.progress.step(1):
                configuration = ResearchConfiguration(
                    ranking_metric=RankingMetric(ranking_metric_label),
                    min_trades_for_confidence=int(min_trades),
                    max_acceptable_drawdown_pct=float(max_drawdown_pct),
                    institutional_min_score=float(institutional_min_score),
                )
                engine = ResearchEngine()
                session = engine.try_execute(tuple(records), configuration)
            with job.progress.step(2):
                pass
            return (session, skip_warnings)

        job = job_manager.submit(
            name=f"Research: {len(choices)} strategy(ies)",
            category=JobCategory.RESEARCH,
            operation=_run_research,
            owner_page="Research Dashboard",
            step_names=RESEARCH_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.research_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("research_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=f"{len(choices)} strategy(ies)")
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Research failed: {current_job.error}")
        render_status_bar(module="Research Dashboard", execution_status=current_job.state.value if current_job else "Ready", job=current_job, **job_manager.status_counts())
        st.stop()

    session, skip_warnings = current_job.result
    for skip_warning in skip_warnings:
        st.warning(skip_warning)

    if session is None:
        st.error("No selected strategy built and backtested successfully.")
        render_status_bar(module="Research Dashboard", execution_status="No Results", **job_manager.status_counts())
        st.stop()

    st.subheader("Research Result")
    if not session.is_successful:
        st.error("Research context failed validation:")
        st.code(session.validation.report())
        render_status_bar(module="Research Dashboard", validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
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

    tabs = st.tabs(["Rankings", "Comparison Table", "Statistics Charts", "Advanced Analytics", "Insights", "Recommendations", "Export"])

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

    with tabs[6]:
        export_json = ResearchSerializer().to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name="research_result.json", mime="application/json")

with info_col:
    render_info_card(
        "Execution Status",
        [
            ("Result", "Success" if session.is_successful else "Failed"),
            ("Strategies analyzed", summary["total_strategies_analyzed"]),
            ("Top strategy", summary["top_strategy_name"] or "—"),
        ],
    )
    render_runtime_monitor(current_job.id, dataset_label=uploaded_file.name if uploaded_file else None, strategy_label=f"{len(choices)} strategy(ies)")

render_status_bar(
    module="Research Dashboard",
    validation_status="Valid" if session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
