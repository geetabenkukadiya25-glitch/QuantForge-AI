"""
Streamlit page: Indicator Explorer.

Browse registered indicators, inspect their metadata/parameters, and
preview a calculation over an uploaded CSV. Phase 6 scope only -- this
page (and the engine behind it) never generates trading signals, never
contains strategy logic, and never executes trades.

CSV loading reuses `app.data_engine.DataLoader` here at the UI-
composition level only; `app.indicator_engine` itself never imports
`app.data_engine`.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of page-level tabs as primary navigation. The indicator browser
(formerly "Indicator Explorer" tab) is now the Explorer's scrollable
list; the calculation preview (formerly "Calculation Preview" tab) is the
Workspace. No `IndicatorEngine` call changed -- only where each already-
existing block renders.
"""

import pandas as pd
import streamlit as st

from app.indicator_engine import (
    IndicatorContext,
    IndicatorEngine,
    IndicatorSerializer,
    IndicatorValidationError,
)
from app.ui.components import ToolbarAction, render_command_bar, render_dataset_picker, render_info_card, render_notification_center, render_shell, render_status_bar, render_toolbar

st.set_page_config(page_title="Indicator Explorer - QuantForge AI", page_icon="📐", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Indicator Explorer")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Indicator Explorer")
st.caption("Browse indicator metadata and preview calculations. This engine never generates trading signals.")

if "indicator_engine" not in st.session_state:
    st.session_state.indicator_engine = IndicatorEngine()
engine: IndicatorEngine = st.session_state.indicator_engine
serializer = IndicatorSerializer()

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    categories = sorted({m.category for m in engine.list_indicators()})
    query = st.text_input("Search by name")
    category = st.selectbox("Category", ["All"] + categories)

    results = engine.search(query=query or None, category=None if category == "All" else category)
    st.caption(f"{len(results)} indicator(s)")

    for meta in results:
        enabled = engine.registry.is_enabled(meta.name)
        with st.expander(f"{'🟢' if enabled else '⚪'} {meta.name} — {meta.category}"):
            st.write(meta.description)
            st.write("**Inputs:**", ", ".join(meta.inputs))
            st.write("**Outputs:**", ", ".join(meta.outputs))
            st.write("**Version:**", meta.version)

            st.write("**Parameters:**")
            if meta.parameters:
                param_rows = [
                    {
                        "name": p.name,
                        "type": p.type,
                        "default": p.default,
                        "minimum": p.minimum,
                        "maximum": p.maximum,
                    }
                    for p in meta.parameters
                ]
                st.dataframe(pd.DataFrame(param_rows), use_container_width=True, hide_index=True)
            else:
                st.write("(none)")

            toggle_col1, toggle_col2 = st.columns(2)
            if enabled:
                if toggle_col1.button("Disable", key=f"disable_{meta.name}"):
                    engine.disable(meta.name)
                    st.rerun()
            else:
                if toggle_col2.button("Enable", key=f"enable_{meta.name}"):
                    engine.enable(meta.name)
                    st.rerun()

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Compute", "run", type="primary"),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically when computing."),
            ToolbarAction("🔄 Refresh", "refresh"),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    st.subheader("Calculation Preview")
    df, dataset_record = render_dataset_picker(page_key="indicator_explorer")

    if df is None:
        st.info("Select or upload a dataset to preview an indicator calculation.")
        render_status_bar(module="Indicator Explorer", execution_status="Awaiting Data")
        st.stop()

    enabled_indicators = engine.list_indicators(include_disabled=False)
    indicator_name = st.selectbox("Indicator", [m.name for m in enabled_indicators])
    metadata = engine.registry.get_metadata(indicator_name)

    params = {}
    if metadata.parameters:
        st.write("Parameters")
        cols = st.columns(len(metadata.parameters))
        for col, spec in zip(cols, metadata.parameters):
            if spec.type == "int":
                params[spec.name] = col.number_input(
                    spec.name, value=int(spec.default), step=1,
                    min_value=int(spec.minimum) if spec.minimum is not None else None,
                )
            elif spec.type == "float":
                params[spec.name] = col.number_input(spec.name, value=float(spec.default))
            elif spec.type == "bool":
                params[spec.name] = col.checkbox(spec.name, value=bool(spec.default))
            else:
                params[spec.name] = col.text_input(spec.name, value=str(spec.default))

    if toolbar_clicked.get("run"):
        context = IndicatorContext(data=df, symbol=uploaded_file.name, timeframe=None)
        try:
            result = engine.compute(indicator_name, context, **params)
        except IndicatorValidationError as exc:
            st.error(f"Validation failed: {exc}")
            render_status_bar(module="Indicator Explorer", execution_status="Validation Failed")
            st.stop()
        else:
            st.session_state.indicator_preview_result = result

    result = st.session_state.get("indicator_preview_result")
    if result is not None:
        preview_df = pd.DataFrame(
            {name: series for name, series in result.values.items()},
            index=pd.to_datetime(list(result.datetime_index)),
        )
        preview_tab, export_tab = st.tabs(["Preview", "Export"])
        with preview_tab:
            st.line_chart(preview_df)
            st.dataframe(preview_df.tail(20), use_container_width=True)
        with export_tab:
            export_json = serializer.to_json(result)
            st.code(export_json, language="json")
            st.download_button("Download raw result (JSON)", data=export_json, file_name=f"{indicator_name}_result.json", mime="application/json")

with info_col:
    st.subheader("Information")
    render_info_card("Registry", [("Total indicators", len(engine.list_indicators())), ("Enabled", len(engine.list_indicators(include_disabled=False)))])
    result = st.session_state.get("indicator_preview_result")
    if result is not None:
        render_info_card("Last Computation", [("Outputs", ", ".join(result.values.keys()))])

render_status_bar(
    module="Indicator Explorer",
    execution_status="Completed" if st.session_state.get("indicator_preview_result") is not None else "Ready",
)
