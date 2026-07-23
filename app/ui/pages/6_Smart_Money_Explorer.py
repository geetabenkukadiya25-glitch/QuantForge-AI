"""
Streamlit page: Smart Money Explorer.

Browse registered Smart Money detectors, inspect their metadata/
parameters, and preview a detection run over an uploaded CSV, plotted on
a candlestick chart. Phase 7 scope only -- this page (and the engine
behind it) never generates trading signals, never contains strategy
logic, and never executes trades.

CSV loading and charting reuse `app.data_engine`/`app.chart_engine` here
at the UI-composition level only; `app.smart_money_engine` itself never
imports either.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of page-level tabs as primary navigation. The detector browser
(formerly "Detector Explorer" tab) is now the Explorer's scrollable list;
the detection preview (formerly "Detection Preview" tab) is the
Workspace. No `SmartMoneyEngine` call changed -- only where each already-
existing block renders.
"""

import pandas as pd
import streamlit as st

from app.chart_engine import ChartConfig, ChartEngine, DrawingManager, HorizontalLine, Rectangle
from app.smart_money_engine import SMCContext, SmartMoneyEngine, SMCValidationError
from app.ui.components import ToolbarAction, render_command_bar, render_dataset_picker, render_info_card, render_notification_center, render_shell, render_status_bar, render_toolbar

st.set_page_config(page_title="Smart Money Explorer - QuantForge AI", page_icon="🧠", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Smart Money Explorer")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Smart Money Explorer")
st.caption(
    "Browse Smart Money Concepts detectors and preview detections. "
    "This engine never generates trading signals."
)

if "smc_engine" not in st.session_state:
    st.session_state.smc_engine = SmartMoneyEngine()
engine: SmartMoneyEngine = st.session_state.smc_engine
chart_engine = ChartEngine()

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    categories = sorted({m.category for m in engine.list_detectors()})
    query = st.text_input("Search by name")
    category = st.selectbox("Category", ["All"] + categories)

    results = engine.search(query=query or None, category=None if category == "All" else category)
    st.caption(f"{len(results)} detector(s)")

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
            ToolbarAction("▶ Run", "run", type="primary"),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically when running a detector."),
            ToolbarAction("🔄 Refresh", "refresh"),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    st.subheader("Detection Preview")
    df, dataset_record = render_dataset_picker(page_key="smart_money_explorer")

    if df is None:
        st.info("Select or upload a dataset to preview a detector run.")
        render_status_bar(module="Smart Money Explorer", execution_status="Awaiting Data")
        st.stop()

    enabled_detectors = engine.list_detectors(include_disabled=False)
    detector_name = st.selectbox("Detector", [m.name for m in enabled_detectors])
    metadata = engine.registry.get_metadata(detector_name)

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
            else:
                params[spec.name] = col.text_input(spec.name, value=str(spec.default))

    if toolbar_clicked.get("run"):
        context = SMCContext(data=df, symbol=uploaded_file.name, timeframe=None)
        try:
            result = engine.detect(detector_name, context, **params)
        except SMCValidationError as exc:
            st.error(f"Validation failed: {exc}")
            render_status_bar(module="Smart Money Explorer", execution_status="Validation Failed")
            st.stop()
        else:
            st.session_state.smc_preview_result = result

    result = st.session_state.get("smc_preview_result")
    if result is not None:
        st.success(f"{len(result.detections)} detection(s) found.")

        drawings = DrawingManager()
        for d in result.detections:
            ts = df["Datetime"].iloc[d.index]
            if d.top is not None and d.bottom is not None:
                end_ts = df["Datetime"].iloc[d.end_index] if d.end_index is not None else ts
                drawings.add(Rectangle(x0=ts, y0=d.bottom, x1=end_ts, y1=d.top))
            elif d.price is not None:
                drawings.add(HorizontalLine(price=d.price, label=d.label))

        fig = chart_engine.render(df, config=ChartConfig(theme="dark"), drawings=drawings)
        st.plotly_chart(fig, use_container_width=True)

        detection_rows = [d.to_dict() for d in result.detections]
        st.dataframe(pd.DataFrame(detection_rows), use_container_width=True)

with info_col:
    st.subheader("Information")
    render_info_card("Registry", [("Total detectors", len(engine.list_detectors())), ("Enabled", len(engine.list_detectors(include_disabled=False)))])
    result = st.session_state.get("smc_preview_result")
    if result is not None:
        render_info_card("Last Detection Run", [("Detections", len(result.detections))])

render_status_bar(
    module="Smart Money Explorer",
    execution_status="Completed" if st.session_state.get("smc_preview_result") is not None else "Ready",
)
