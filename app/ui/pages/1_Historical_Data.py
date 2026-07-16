"""
Streamlit page: Historical Data.

Lets a user browse/upload a CSV (standard or MT5 export format), preview
it, inspect summary statistics, and generate a data quality report.
Phase 2 scope only -- no strategy logic, indicators, AI, or backtesting.
"""

import tempfile
from pathlib import Path

import streamlit as st

from app.data_engine import (
    CSVFormatError,
    DataCleaner,
    DataLoader,
    generate_quality_report,
)

st.set_page_config(page_title="Historical Data - QuantForge AI", page_icon="📈", layout="wide")

st.title("Historical Data")
st.caption("Load, validate, and inspect historical OHLCV data.")

loader = DataLoader()
cleaner = DataCleaner()

uploaded_file = st.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])
clean_on_load = st.checkbox("Clean on load (sort, de-duplicate, drop unparseable rows)", value=True)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        df = loader.load_csv(tmp_path, clean=clean_on_load)
    except CSVFormatError as exc:
        st.error(f"Could not load file: {exc}")
    else:
        st.success(f"Loaded {len(df):,} candles from '{uploaded_file.name}'.")

        st.subheader("Preview")
        head_col, tail_col = st.columns(2)
        with head_col:
            st.caption("First rows")
            st.dataframe(loader.preview_head(df), use_container_width=True)
        with tail_col:
            st.caption("Last rows")
            st.dataframe(loader.preview_tail(df), use_container_width=True)

        st.subheader("Statistics")
        stats = loader.statistics(df)
        cols = st.columns(4)
        cols[0].metric("Candles", f"{stats['num_candles']:,}")
        cols[1].metric("Detected timeframe", stats["detected_timeframe"] or "—")
        cols[2].metric("Missing candles", f"{stats['missing_candles']:,}")
        cols[3].metric("Duplicate candles", f"{stats['duplicate_candles']:,}")
        st.write(
            f"Date range: **{stats['date_range_start']}** → **{stats['date_range_end']}**  \n"
            f"Memory usage: **{stats['memory_usage_bytes'] / 1024:.1f} KB**"
        )

        st.subheader("Data Quality Report")
        report = generate_quality_report(df)
        report_dict = {key: str(value) for key, value in report.to_dict().items()}
        st.json(report_dict, expanded=False)

    finally:
        tmp_path.unlink(missing_ok=True)
else:
    st.info("Upload a CSV file to get started.")
