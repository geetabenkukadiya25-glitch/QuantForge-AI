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
"""

from pathlib import Path

import streamlit as st

from app.ea_generator import EAGeneratorConfiguration, EAGeneratorEngine, EAGeneratorReport, EAGeneratorSerializer
from app.indicator_engine import IndicatorRegistry
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry
from app.strategy_builder import StrategyBuilder, StrategyContext

st.set_page_config(page_title="EA Generator - QuantForge AI", page_icon="\U0001f9be", layout="wide")

st.title("EA Generator")
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

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("1. Strategy Selection")
examples = _load_examples()
if not examples:
    st.sidebar.error("No SDL example strategies found.")
    st.stop()
selected_name = st.sidebar.selectbox("SDL example strategy", list(examples.keys()))

st.sidebar.header("2. Output")
output_filename = st.sidebar.text_input("Output filename", value="GeneratedEA.mq5")
ea_name = st.sidebar.text_input("EA display name (optional)", value="")
author = st.sidebar.text_input("Author", value="QuantForge AI")

st.sidebar.header("3. Risk Parameters")
magic_number = st.sidebar.number_input("Magic number", min_value=0, value=100000, step=1)
lot_size = st.sidebar.number_input("Lot size", min_value=0.01, value=0.1, step=0.01)
stop_loss_points = st.sidebar.number_input("Stop loss (points)", min_value=0.0, value=200.0, step=10.0)
take_profit_points = st.sidebar.number_input("Take profit (points)", min_value=0.0, value=400.0, step=10.0)
max_open_positions = st.sidebar.number_input("Max open positions", min_value=1, value=1, step=1)
include_comments = st.sidebar.checkbox("Include explanatory comments", value=True)


def _build_strategy_model():
    try:
        raw_data = parser.parse_file(examples[selected_name])
    except SDLParseError as exc:
        st.sidebar.warning(f"'{selected_name}': could not parse ({exc}).")
        return None

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        st.sidebar.warning(f"'{selected_name}': failed SDL validation, cannot generate.")
        return None

    strategy_context = StrategyContext(sdl_definition=sdl_result.definition, indicator_registry=st.session_state.indicator_registry, smc_registry=st.session_state.smc_registry)
    build_result = strategy_builder.try_build(strategy_context)
    if not build_result.is_valid:
        st.sidebar.warning(f"'{selected_name}': failed Strategy Builder validation, cannot generate.")
        return None

    return build_result.model


if st.sidebar.button("Generate EA", type="primary"):
    with st.spinner("Building strategy model..."):
        model = _build_strategy_model()

    if model is None:
        st.error("Could not build the selected strategy. See sidebar warnings.")
        st.stop()

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
    with st.spinner("Generating EA source code..."):
        st.session_state.ea_session = engine.try_execute(model, configuration)

if "ea_session" not in st.session_state:
    st.info("Select a strategy and click 'Generate EA' in the sidebar.")
    st.stop()

session = st.session_state.ea_session
st.subheader("Generation Result")
if not session.is_successful:
    st.error("EA generation context failed validation:")
    st.code(session.validation.report())
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

tabs = st.tabs(["Source Preview", "Inputs", "Indicators", "Risk Report", "Trade Management", "Generation Report"])

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

with st.expander("Raw EAGeneratorResult (JSON)"):
    st.code(serializer.to_json(result), language="json")
