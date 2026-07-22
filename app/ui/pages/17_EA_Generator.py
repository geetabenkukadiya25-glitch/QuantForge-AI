"""
Streamlit page: EA Generator.

Generates production-quality-skeleton MetaTrader 5 (MQL5) Expert
Advisor source code from an already-built `StrategyModel`. This page
(and the module behind it) is an OFFLINE CODE GENERATOR ONLY -- it
never compiles MT5, never executes trades, never connects to a broker,
never calls MetaTrader, and never calls any external API. It consumes
ONLY an already-built Strategy Builder `StrategyModel` -- it never
duplicates SDL, never duplicates the Strategy Builder, and never
rebuilds any prior engine.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No engine, SDL, or EA
Generator Engine call changed -- every `st.sidebar.X(...)` became
`st.X(...)` inside a `with explorer_col:` block, and "Generate EA" moved
into the toolbar as "Run".
"""

from pathlib import Path

import streamlit as st

from app.ea_generator import EAGeneratorConfiguration, EAGeneratorEngine, EAGeneratorReport, EAGeneratorSerializer
from app.indicator_engine import IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar
from app.ui.progress import EA_GENERATOR_STEPS

st.set_page_config(page_title="EA Generator - QuantForge AI", page_icon="\U0001f9be", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("EA Generator")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("EA Generator")
st.caption(
    "Generates MQL5 Expert Advisor source code from an already-built strategy. This module is an OFFLINE CODE "
    "GENERATOR ONLY -- it never compiles MT5, never executes trades, never connects to a broker, and never calls "
    "MetaTrader or any external API. Review every generated TODO before compiling in MetaEditor."
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

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


explorer_col, workspace_col, info_col = render_shell()

with info_col:
    st.subheader("Information")

with explorer_col:
    st.subheader("Explorer")
    st.header("1. Strategy Selection")
    examples = _load_examples()
    if not examples:
        st.error("No SDL example strategies found.")
        render_status_bar(module="EA Generator", execution_status="No Examples", **job_manager.status_counts())
        st.stop()
    selected_name = st.selectbox("SDL example strategy", list(examples.keys()))

    st.header("2. Output")
    output_filename = st.text_input("Output filename", value="GeneratedEA.mq5")
    ea_name = st.text_input("EA display name (optional)", value="")
    author = st.text_input("Author", value="QuantForge AI")

    st.header("3. Risk Parameters")
    magic_number = st.number_input("Magic number", min_value=0, value=100000, step=1)
    lot_size = st.number_input("Lot size", min_value=0.01, value=0.1, step=0.01)
    stop_loss_points = st.number_input("Stop loss (points)", min_value=0.0, value=200.0, step=10.0)
    take_profit_points = st.number_input("Take profit (points)", min_value=0.0, value=400.0, step=10.0)
    max_open_positions = st.number_input("Max open positions", min_value=1, value=1, step=1)
    include_comments = st.checkbox("Include explanatory comments", value=True)

with info_col:
    render_info_card(
        "Configuration",
        [
            ("Strategy", selected_name),
            ("Output filename", output_filename),
            ("Magic number", int(magic_number)),
        ],
    )


def _build_strategy_model(warnings: list[str], indicator_registry, smc_registry):
    # Runs inside the Job Manager's dispatcher thread -- never calls
    # `st.*` directly (including `st.session_state`, which has no
    # meaning off the main script thread); the registries are passed in
    # as plain objects, captured in the main thread before submission.
    # Skip reasons are collected into `warnings` and displayed by the
    # main script thread once the job completes.
    try:
        raw_data = parser.parse_file(examples[selected_name])
    except SDLParseError as exc:
        warnings.append(f"'{selected_name}': could not parse ({exc}).")
        return None

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        warnings.append(f"'{selected_name}': failed SDL validation, cannot generate.")
        return None

    strategy_context = StrategyContext(sdl_definition=sdl_result.definition, indicator_registry=indicator_registry, smc_registry=smc_registry)
    build_result = strategy_builder.try_build(strategy_context)
    if not build_result.is_valid:
        warnings.append(f"'{selected_name}': failed Strategy Builder validation, cannot generate.")
        return None

    return build_result.model


with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("ea_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for the selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="This page generates MQL5 source only -- it never compiles MT5."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for EA Generator in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("stop") and _toolbar_job is not None:
        job_manager.cancel(_toolbar_job.id)
        notify("warning", f"Cancel requested: {_toolbar_job.name}")
        st.rerun()

    if toolbar_clicked.get("run"):
        def _run_ea_generation(
            job, output_filename=output_filename, ea_name=ea_name, author=author, magic_number=magic_number,
            lot_size=lot_size, stop_loss_points=stop_loss_points, take_profit_points=take_profit_points,
            max_open_positions=max_open_positions, include_comments=include_comments,
            indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry,
        ):
            skip_warnings: list[str] = []
            with job.progress.step(0):
                model = _build_strategy_model(skip_warnings, indicator_registry, smc_registry)

            if model is None:
                return (None, skip_warnings)

            with job.progress.step(1):
                configuration = EAGeneratorConfiguration(
                    output_filename=output_filename,
                    ea_name=ea_name or None,
                    author=author,
                    magic_number=int(magic_number),
                    lot_size=float(lot_size),
                    stop_loss_points=float(stop_loss_points),
                    take_profit_points=float(take_profit_points),
                    max_open_positions=int(max_open_positions),
                    include_comments=bool(include_comments),
                )
                engine = EAGeneratorEngine()
                session = engine.try_execute(model, configuration)
            with job.progress.step(2):
                pass
            return (session, skip_warnings)

        job = job_manager.submit(
            name=f"EA Generation: {selected_name}",
            category=JobCategory.EA_GENERATION,
            operation=_run_ea_generation,
            owner_page="EA Generator",
            step_names=EA_GENERATOR_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.ea_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("ea_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, strategy_label=selected_name)
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"EA generation failed: {current_job.error}")
        elif current_job is None:
            st.info("Select a strategy and click 'Run' in the toolbar.")
        render_status_bar(module="EA Generator", execution_status=current_job.state.value if current_job else "Ready", job=current_job, **job_manager.status_counts())
        st.stop()

    session, skip_warnings = current_job.result
    for skip_warning in skip_warnings:
        st.warning(skip_warning)

    if session is None:
        st.error("Could not build the selected strategy. See warnings above.")
        render_status_bar(module="EA Generator", execution_status="Build Failed", **job_manager.status_counts())
        st.stop()

    st.subheader("Generation Result")
    if not session.is_successful:
        st.error("EA generation context failed validation:")
        st.code(session.validation.report())
        render_status_bar(module="EA Generator", validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
        st.stop()

    for warning in session.validation.warnings:
        st.info(str(warning))

    result = session.result
    report = EAGeneratorReport(result)
    serializer = EAGeneratorSerializer()

    st.subheader("Metadata")
    summary = report.summary()
    cols = st.columns(4)
    cols[0].metric("Indicators", summary["total_indicators"])
    cols[1].metric("Detectors", summary["total_detectors"])
    cols[2].metric("Rules", summary["total_rules"])
    cols[3].metric("Source lines", summary["source_line_count"])
    st.write(f"**Strategy id:** {summary['strategy_id']}")
    st.write(f"**Output filename:** {summary['output_filename']}")
    st.caption(f"Checksum: {result.checksum}")

    st.download_button(
        "Download generated source",
        data=result.source_code,
        file_name=result.metadata.output_filename,
        mime="text/plain",
    )

    tabs = st.tabs(["Source Preview", "Inputs", "Indicators", "Risk Report", "Trade Management", "Generation Report", "Export"])

    with tabs[0]:
        st.code(report.source_preview(max_lines=200), language="cpp")

    with tabs[1]:
        st.dataframe(report.inputs_table(), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.dataframe(report.indicators_table(), use_container_width=True, hide_index=True)

    with tabs[3]:
        st.json(report.risk_report())

    with tabs[4]:
        st.markdown("**Filters**")
        st.dataframe(report.filters_table(), use_container_width=True, hide_index=True)
        st.markdown("**Entry Rules**")
        st.dataframe(report.entry_rules_table(), use_container_width=True, hide_index=True)
        st.markdown("**Exit Rules**")
        st.dataframe(report.exit_rules_table(), use_container_width=True, hide_index=True)

    with tabs[5]:
        st.json(summary)

    with tabs[6]:
        export_json = serializer.to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name="ea_generator_result.json", mime="application/json")

with info_col:
    render_info_card(
        "Execution Status",
        [
            ("Result", "Success" if session.is_successful else "Failed"),
            ("Source lines", summary["source_line_count"]),
            ("Output filename", summary["output_filename"]),
        ],
    )
    render_runtime_monitor(current_job.id, strategy_label=selected_name)

render_status_bar(
    module="EA Generator",
    strategy_status=selected_name,
    validation_status="Valid" if session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
