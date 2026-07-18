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
from app.smart_money_engine import SMCRegistry

st.set_page_config(page_title="Extraction Dashboard - QuantForge AI", page_icon="🧩", layout="wide")

st.title("AI Strategy Extraction Engine")
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

st.sidebar.header("1. Source Document")
source_type_label = st.sidebar.selectbox("Source type", [s.value for s in SourceType])
use_sample = st.sidebar.checkbox("Load sample document", value=True)
raw_text = st.text_area("Document text", value=SAMPLE_TEXT if use_sample else "", height=320)

st.sidebar.header("2. Configuration")
min_confidence = st.sidebar.slider("Min confidence threshold", 0.0, 1.0, 0.3, 0.05)
name_hint = st.sidebar.text_input("Strategy name override (optional)")

if st.sidebar.button("Run Extraction", type="primary"):
    configuration = ExtractionConfiguration(min_confidence_threshold=min_confidence, strategy_name_hint=name_hint or None)
    session = engine.try_execute(
        raw_text, SourceType(source_type_label), configuration,
        indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry,
    )
    st.session_state.extraction_session = session
    if session.is_successful:
        registry.register(session.result)

if "extraction_session" not in st.session_state:
    st.info("Paste a document (or use the sample) and click 'Run Extraction' in the sidebar.")
    st.stop()

session = st.session_state.extraction_session
if not session.is_successful:
    st.error("Extraction failed validation:")
    st.code(session.validation.report())
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
    with st.expander("Raw ExtractionResult (JSON)"):
        st.code(ExtractionSerializer().to_json(result), language="json")

with tabs[6]:
    history = registry.list()
    if history:
        st.dataframe(
            pd.DataFrame([{"extraction_id": m.extraction_id, "source_type": m.source_type, "result_version": m.result_version} for m in history]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No extractions registered yet this session.")
