"""
Streamlit page: Extraction Dashboard.

Converts external strategy document text (YouTube transcript, PDF,
Markdown, plain text, Pine Script, MQL4, MQL5, EasyLanguage, pseudocode,
OCR text -- already obtained by the user; this page never fetches,
downloads, or OCRs anything itself) into a draft SDL document, a
confidence report, and a missing-information report. This module is a
deterministic, offline, pattern/keyword-matching pipeline -- NOT a
generative AI model, and it never calls an external API. It MUST NOT
generate trading ideas; it only extracts information already present in
the supplied text. Every output is an explicit DRAFT requiring human
review and approval before use (see `PROJECT_VISION.md`'s "AI assists,
humans approve" principle and its YouTube strategy workflow).

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar and a
bottom status bar. Its existing results tabs (Overview / Indicators &
Detectors / Rules / Risk & Sessions / Confidence & Missing Info /
Generated SDL / History) are unchanged. No `AIStrategyExtractionEngine`
call changed -- every `st.sidebar.X(...)` became `st.X(...)` inside a
`with explorer_col:` block, and "Run Extraction" moved into the toolbar
as "Run".
"""

import pandas as pd
import streamlit as st

from app.ai_extraction import (
    AIStrategyExtractionEngine,
    ExtractionConfiguration,
    ExtractionRegistry,
    ExtractionReport,
    ExtractionSerializer,
    SourceType,
)
from app.indicator_engine import IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
from app.smart_money_engine import SMCRegistry
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar

EXTRACTION_STEPS = ["Extracting Strategy"]

st.set_page_config(page_title="Extraction Dashboard - QuantForge AI", page_icon="🧩", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("AI Strategy Extraction Engine")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Extraction Dashboard")
st.caption(
    "Converts an already-obtained strategy document (transcript, PDF text, Pine Script, MQL4/5, EasyLanguage, "
    "pseudocode, OCR text, ...) into a draft SDL document. This module is NOT a generative AI model -- it only "
    "extracts information already present in the text, never invents trading logic, and every output is a DRAFT "
    "requiring human review before use."
)

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()
if "extraction_registry" not in st.session_state:
    st.session_state.extraction_registry = ExtractionRegistry()

engine = AIStrategyExtractionEngine()
registry: ExtractionRegistry = st.session_state.extraction_registry
job_manager = get_job_manager()

SAMPLE_TEXT = """# Golden Cross Trend Strategy

A simple trend-following strategy using two moving averages on the London session.

## Indicators
- SMA(20) fast moving average
- SMA(50) slow moving average
- RSI(14) for confirmation

## Entry Rules
- Buy when fast_ma crosses above slow_ma during the London session
- Enter long when RSI is above 50

## Exit Rules
- Exit when fast_ma crosses below slow_ma
- Take profit at 40 pips

## Risk Management
- Risk 1% per trade
- Stop loss 20 pips
- Risk reward 1:2

## Timeframe
Trade on the H1 timeframe.
"""

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    st.header("1. Source Document")
    source_type_label = st.selectbox("Source type", [s.value for s in SourceType])
    use_sample = st.checkbox("Load sample document", value=True)

    st.header("2. Configuration")
    min_confidence = st.slider("Min confidence threshold", 0.0, 1.0, 0.3, 0.05)
    name_hint = st.text_input("Strategy name override (optional)")

with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("extraction_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically as part of extraction."),
            ToolbarAction("🔄 Refresh", "refresh"),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("stop") and _toolbar_job is not None:
        job_manager.cancel(_toolbar_job.id)
        notify("warning", f"Cancel requested: {_toolbar_job.name}")
        st.rerun()

    raw_text = st.text_area("Document text", value=SAMPLE_TEXT if use_sample else "", height=320)

    if toolbar_clicked.get("run"):
        def _run_extraction(
            job, raw_text=raw_text, source_type_label=source_type_label, min_confidence=min_confidence, name_hint=name_hint,
            indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry, registry=registry,
        ):
            # `indicator_registry`/`smc_registry`/`registry` are captured
            # here (main thread, at closure-definition time) since
            # `st.session_state` has no meaning inside the dispatcher
            # thread this runs on.
            with job.progress.step(0):
                configuration = ExtractionConfiguration(min_confidence_threshold=min_confidence, strategy_name_hint=name_hint or None)
                session = engine.try_execute(
                    raw_text, SourceType(source_type_label), configuration,
                    indicator_registry=indicator_registry, smc_registry=smc_registry,
                )
                if session.is_successful:
                    registry.register(session.result)
            return session

        job = job_manager.submit(
            name="Strategy Extraction",
            category=JobCategory.EXTRACTION,
            operation=_run_extraction,
            owner_page="Extraction Dashboard",
            step_names=EXTRACTION_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.extraction_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("extraction_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id, strategy_label=name_hint or None)
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Extraction failed: {current_job.error}")
        elif current_job is None:
            st.info("Paste a document (or use the sample) and click 'Run' in the toolbar.")
        render_status_bar(module="Extraction Dashboard", execution_status=current_job.state.value if current_job else "Ready", job=current_job, **job_manager.status_counts())
        st.stop()

    session = current_job.result
    if not session.is_successful:
        st.error("Extraction failed validation:")
        st.code(session.validation.report())
        render_status_bar(module="Extraction Dashboard", validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
        st.stop()

    result = session.result
    report = ExtractionReport(result)

    st.success(report.executive_summary())
    st.caption(f"Checksum: {result.checksum}")

    tabs = st.tabs(["Overview", "Indicators & Detectors", "Rules", "Risk & Sessions", "Confidence & Missing Info", "Generated SDL", "History"])

    with tabs[0]:
        stats = report.statistics()
        cols = st.columns(4)
        cols[0].metric("Indicators", stats["indicator_count"])
        cols[1].metric("Entry Rules", stats["entry_rule_count"])
        cols[2].metric("Risk Statements", stats["risk_mention_count"])
        cols[3].metric("Overall Confidence", f"{stats['overall_confidence']:.0%}")
        st.write(f"**Strategy Name:** {result.strategy_name}")
        st.write(f"**Description:** {result.description or '_(none detected)_'}")
        st.write(f"**SDL schema valid:** {'✅ Yes' if result.sdl_validation.is_valid else '❌ No'}")
        if result.unknown_items:
            st.markdown("**Unknown items** (mentioned but not a registered name):")
            for item in result.unknown_items:
                st.markdown(f"- {item}")

    with tabs[1]:
        st.markdown("**Indicators**")
        st.dataframe(report.indicators_table(), use_container_width=True, hide_index=True)
        st.markdown("**Smart Money Detectors**")
        st.dataframe(report.detectors_table(), use_container_width=True, hide_index=True)
        st.markdown("**Parameters**")
        st.dataframe(report.parameters_table(), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown("**Entry Rules**")
        st.dataframe(report.entry_rules_table(), use_container_width=True, hide_index=True)
        st.markdown("**Exit Rules**")
        st.dataframe(report.exit_rules_table(), use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("**Risk Management**")
        st.dataframe(report.risk_table(), use_container_width=True, hide_index=True)
        st.markdown("**Sessions**")
        st.dataframe(report.sessions_table(), use_container_width=True, hide_index=True)
        st.markdown("**Timeframes**")
        st.dataframe(report.timeframes_table(), use_container_width=True, hide_index=True)

    with tabs[4]:
        st.markdown("**Confidence by category**")
        st.dataframe(report.confidence_table(), use_container_width=True, hide_index=True)
        st.markdown("**Missing information**")
        st.write(list(result.missing_information.missing_items))
        st.dataframe(report.missing_information_table(), use_container_width=True, hide_index=True)

    with tabs[5]:
        st.warning("This is a DRAFT. Requires human review and approval before it can be built by Strategy Builder or backtested.")
        if not result.sdl_validation.is_valid:
            st.error("SDL schema errors:")
            for err in result.sdl_validation.errors:
                st.markdown(f"- {err}")
        st.code(result.generated_sdl_yaml, language="yaml")
        st.download_button("Download draft SDL (.yaml)", result.generated_sdl_yaml, file_name=f"{result.strategy_name.lower().replace(' ', '_')}_draft.yaml")
        export_json = ExtractionSerializer().to_json(result)
        with st.expander("Raw ExtractionResult (JSON)"):
            st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name="extraction_result.json", mime="application/json")

    with tabs[6]:
        history = registry.list()
        if history:
            st.dataframe(
                pd.DataFrame([{"extraction_id": m.extraction_id, "source_type": m.source_type, "result_version": m.result_version} for m in history]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No extractions registered yet this session.")

with info_col:
    st.subheader("Information")
    render_info_card(
        "Extraction",
        [
            ("Strategy name", result.strategy_name),
            ("SDL schema valid", "Yes" if result.sdl_validation.is_valid else "No"),
            ("Overall confidence", f"{report.statistics()['overall_confidence']:.0%}"),
        ],
    )
    render_runtime_monitor(current_job.id, strategy_label=result.strategy_name)

render_status_bar(
    module="Extraction Dashboard",
    strategy_status=result.strategy_name,
    validation_status="Valid" if session.is_successful else "Invalid",
    **job_manager.status_counts(),
    execution_status="Completed",
)
