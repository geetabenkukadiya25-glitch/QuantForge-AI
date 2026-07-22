"""
Streamlit page: Strategy Builder Explorer.

Open an SDL strategy, build it into an executable `StrategyModel`, and
inspect its validation report, dependency graph, execution pipeline, and
summary. Phase 8 scope only -- this page (and the module behind it)
never executes trades, places orders, backtests, optimizes parameters,
or generates AI decisions.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No engine, SDL, or Strategy
Builder call changed -- every `st.sidebar.X(...)` became `st.X(...)`
inside a `with explorer_col:` block.
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
from app.ui.components import ToolbarAction, render_command_bar, render_info_card, render_notification_center, render_shell, render_status_bar, render_toolbar

st.set_page_config(page_title="Strategy Builder Explorer - QuantForge AI", page_icon="🏗️", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Strategy Builder Explorer")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Strategy Builder Explorer")
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


explorer_col, workspace_col, info_col = render_shell()

with info_col:
    st.subheader("Information")

with explorer_col:
    st.subheader("Explorer")
    st.header("Open Strategy")
    examples = _load_examples()
    choice = st.selectbox("SDL example", list(examples.keys()))

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for the selected strategy."),
            ToolbarAction("⚙ Compile", "compile", enabled=False, disabled_reason="Build runs automatically for the selected strategy."),
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("📜 History", "history", enabled=False, disabled_reason="Run history is not available for Strategy Builder Explorer in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    try:
        raw_data = parser.parse_file(examples[choice])
    except SDLParseError as exc:
        st.error(f"Could not parse example: {exc}")
        render_status_bar(module="Strategy Builder Explorer", execution_status="Invalid Strategy")
        st.stop()

    sdl_result = SDLValidator().validate(raw_data)
    if not sdl_result.is_valid:
        st.error("This SDL document is invalid at the SDL layer (Phase 4):")
        st.code(sdl_result.report())
        render_status_bar(module="Strategy Builder Explorer", execution_status="Invalid Strategy")
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
        render_status_bar(module="Strategy Builder Explorer", validation_status="Invalid", execution_status="Build Failed")
        st.stop()

    model = result.model

    tabs = st.tabs(["Overview", "Dependency Graph", "Execution Pipeline", "Export"])

    with tabs[0]:
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

    with tabs[1]:
        st.subheader("Strategy Dependency Graph")
        edge_rows = [{"source": e.source, "target": e.target} for e in model.dependency_graph.edges]
        if edge_rows:
            st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No dependency edges (no component references any other).")
        st.write("Nodes:", ", ".join(model.dependency_graph.nodes) or "(none)")

    with tabs[2]:
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

    with tabs[3]:
        export_json = serializer.to_json(model)
        st.code(export_json, language="json")
        st.download_button("Download raw model (JSON)", data=export_json, file_name=f"{choice}_strategy_model.json", mime="application/json")

with info_col:
    render_info_card(
        "Strategy",
        [
            ("Name", model.metadata.name),
            ("ID", model.metadata.id),
            ("Indicators", len(model.indicators)),
            ("Rules", len(model.rules)),
        ],
    )

render_status_bar(
    module="Strategy Builder Explorer",
    strategy_status=model.metadata.name,
    validation_status="Valid" if result.is_valid else "Invalid",
    execution_status="Completed",
)
