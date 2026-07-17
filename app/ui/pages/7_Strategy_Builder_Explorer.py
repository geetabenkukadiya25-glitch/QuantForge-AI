"""
Streamlit page: Strategy Builder Explorer.

Open an SDL strategy, build it into an executable `StrategyModel`, and
inspect its validation report, dependency graph, execution pipeline, and
summary. Phase 8 scope only -- this page (and the module behind it)
never executes trades, places orders, backtests, optimizes parameters,
or generates AI decisions.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.indicator_engine import IndicatorRegistry
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry
from app.strategy_builder import StrategyBuilder, StrategyContext, StrategySerializer

st.set_page_config(page_title="Strategy Builder Explorer - QuantForge AI", page_icon="🏗️", layout="wide")

st.title("Strategy Builder Explorer")
st.caption(
    "Build executable strategy models from SDL. This module never executes trades, "
    "backtests, optimizes, or generates AI decisions."
)

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()

parser = StrategyParser()
serializer = StrategySerializer()
builder = StrategyBuilder()

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("Open Strategy")
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

context = StrategyContext(
    sdl_definition=sdl_result.definition,
    indicator_registry=st.session_state.indicator_registry,
    smc_registry=st.session_state.smc_registry,
)

result = builder.try_build(context)

st.subheader("Validation Report")
if result.is_valid:
    st.success(f"Valid ({len(result.validation.warnings)} warning(s))")
else:
    st.error(f"Invalid ({len(result.validation.errors)} error(s))")
for issue in result.validation.errors:
    st.markdown(f"- 🔴 **{issue.path}** — {issue.message}")
for issue in result.validation.warnings:
    st.markdown(f"- 🟡 **{issue.path}** — {issue.message}")

if not result.is_valid:
    st.stop()

model = result.model

st.subheader("Strategy Summary")
cols = st.columns(4)
cols[0].metric("Indicators", len(model.indicators))
cols[1].metric("Detectors", len(model.detectors))
cols[2].metric("Rules", len(model.rules))
cols[3].metric("Execution steps", len(model.execution_pipeline.steps))
st.write(f"**{model.metadata.name}** (`{model.metadata.id}`)")
st.write(model.metadata.description or "_No description._")
st.write("Symbols:", ", ".join(model.context_requirement.symbols))
st.write("Timeframes:", ", ".join(model.context_requirement.timeframes))
st.write("Checksum:", model.checksum)

st.subheader("Strategy Dependency Graph")
edge_rows = [{"source": e.source, "target": e.target} for e in model.dependency_graph.edges]
if edge_rows:
    st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)
else:
    st.info("No dependency edges (no component references any other).")
st.write("Nodes:", ", ".join(model.dependency_graph.nodes) or "(none)")

st.subheader("Execution Pipeline Preview")
st.code(model.execution_pipeline.describe(), language=None)
pipeline_rows = [
    {
        "step": s.step_index + 1,
        "component": s.component_name,
        "kind": s.component_kind,
        "depends_on": ", ".join(s.depends_on),
    }
    for s in model.execution_pipeline.steps
]
st.dataframe(pd.DataFrame(pipeline_rows), use_container_width=True, hide_index=True)

with st.expander("Raw StrategyModel (JSON)"):
    st.code(serializer.to_json(model), language="json")
