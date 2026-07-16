"""
Streamlit page: Indicator Explorer.

Browse registered indicators, inspect their metadata/parameters, and
preview a calculation over an uploaded CSV. Phase 6 scope only -- this
page (and the engine behind it) never generates trading signals, never
contains strategy logic, and never executes trades.

CSV loading reuses `app.data_engine.DataLoader` here at the UI-
composition level only; `app.indicator_engine` itself never imports
`app.data_engine`.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import (
    IndicatorContext,
    IndicatorEngine,
    IndicatorSerializer,
    IndicatorValidationError,
)

st.set_page_config(page_title="Indicator Explorer - QuantForge AI", page_icon="📐", layout="wide")

st.title("Indicator Explorer")
st.caption("Browse indicator metadata and preview calculations. This engine never generates trading signals.")

if "indicator_engine" not in st.session_state:
    st.session_state.indicator_engine = IndicatorEngine()
engine: IndicatorEngine = st.session_state.indicator_engine
serializer = IndicatorSerializer()
loader = DataLoader()

tab_explorer, tab_preview = st.tabs(["Indicator Explorer", "Calculation Preview"])

with tab_explorer:
    st.subheader("Registered Indicators")

    categories = sorted({m.category for m in engine.list_indicators()})
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
    st.subheader("Calculation Preview")
    uploaded_file = st.file_uploader("CSV file (standard or MT5 export format)", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV file to preview an indicator calculation.")
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

    if st.button("Compute"):
        context = IndicatorContext(data=df, symbol=uploaded_file.name, timeframe=None)
        try:
            result = engine.compute(indicator_name, context, **params)
        except IndicatorValidationError as exc:
            st.error(f"Validation failed: {exc}")
        else:
            preview_df = pd.DataFrame(
                {name: series for name, series in result.values.items()},
                index=pd.to_datetime(list(result.datetime_index)),
            )
            st.line_chart(preview_df)
            st.dataframe(preview_df.tail(20), use_container_width=True)

            with st.expander("Raw IndicatorResult (JSON)"):
                st.code(serializer.to_json(result), language="json")
