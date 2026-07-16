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
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.chart_engine import ChartConfig, ChartEngine, DrawingManager, HorizontalLine, Rectangle
from app.data_engine import CSVFormatError, DataLoader
from app.smart_money_engine import SMCContext, SmartMoneyEngine, SMCValidationError

st.set_page_config(page_title="Smart Money Explorer - QuantForge AI", page_icon="🧠", layout="wide")

st.title("Smart Money Explorer")
st.caption(
    "Browse Smart Money Concepts detectors and preview detections. "
    "This engine never generates trading signals."
)

if "smc_engine" not in st.session_state:
    st.session_state.smc_engine = SmartMoneyEngine()
engine: SmartMoneyEngine = st.session_state.smc_engine
loader = DataLoader()
chart_engine = ChartEngine()

tab_explorer, tab_preview = st.tabs(["Detector Explorer", "Detection Preview"])

with tab_explorer:
    st.subheader("Registered Detectors")

    categories = sorted({m.category for m in engine.list_detectors()})
    col_query, col_category = st.columns(2)
    query = col_query.text_input("Search by name")
    category = col_category.selectbox("Category", ["All"] + categories)

    results = engine.search(query=query or None, category=None if category == "All" else category)

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

with tab_preview:
    st.subheader("Detection Preview")
    uploaded_file = st.file_uploader("CSV file (standard or MT5 export format)", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV file to preview a detector run.")
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)
    try:
        df = loader.load_csv(tmp_path)
    except CSVFormatError as exc:
        st.error(f"Could not load file: {exc}")
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

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

    if st.button("Run detector"):
        context = SMCContext(data=df, symbol=uploaded_file.name, timeframe=None)
        try:
            result = engine.detect(detector_name, context, **params)
        except SMCValidationError as exc:
            st.error(f"Validation failed: {exc}")
        else:
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
