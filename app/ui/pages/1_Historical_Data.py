"""
Streamlit page: Historical Data.

Lets a user browse/upload a CSV (standard or MT5 export format), preview
it, inspect summary statistics, and generate a data quality report.
Phase 2 scope only -- no strategy logic, indicators, AI, or backtesting.

The loaded dataset is persisted in `st.session_state` (via `app.ui.state`)
so it survives navigating to another page and stays available to every
other dashboard (e.g. Backtesting) without re-uploading -- until the user
loads a different file or explicitly clears it.
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
from app.ui.state import clear_dataset, has_dataset, load_dataset, load_metadata, save_dataset

st.set_page_config(page_title="Historical Data - QuantForge AI", page_icon="📈", layout="wide")

st.title("Historical Data")
st.caption("Load, validate, and inspect historical OHLCV data. The loaded dataset stays available to every other dashboard page.")

loader = DataLoader()
cleaner = DataCleaner()


def _render(df, filename: str, stats: dict) -> None:
    st.success(f"Loaded {len(df):,} candles from '{filename}'.")

    st.subheader("Preview")
    head_col, tail_col = st.columns(2)
    with head_col:
        st.caption("First rows")
        st.dataframe(loader.preview_head(df), use_container_width=True)
    with tail_col:
        st.caption("Last rows")
        st.dataframe(loader.preview_tail(df), use_container_width=True)

    st.subheader("Statistics")
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


if "uploader_reset_token" not in st.session_state:
    st.session_state.uploader_reset_token = 0

# Keyed off a token that "Clear dataset" bumps below -- otherwise clearing
# the persisted dataset while the file_uploader widget still holds its
# previous file would just re-persist that same file on the very next
# rerun, silently undoing the clear.
uploaded_file = st.file_uploader(
    "Upload a CSV file (standard or MT5 export format)", type=["csv"], key=f"historical_data_uploader_{st.session_state.uploader_reset_token}"
)
clean_on_load = st.checkbox("Clean on load (sort, de-duplicate, drop unparseable rows)", value=True)
symbol_label = st.text_input("Symbol (optional, for reference only)", value="")

df, filename, stats = None, None, None

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        df = loader.load_csv(tmp_path, clean=clean_on_load)
    except CSVFormatError as exc:
        st.error(f"Could not load file: {exc}")
        df = None
    else:
        filename = uploaded_file.name
        stats = loader.statistics(df)
        save_dataset(df, filename=filename, symbol=symbol_label or None, timeframe=stats["detected_timeframe"], statistics=stats)
    finally:
        tmp_path.unlink(missing_ok=True)

elif has_dataset():
    df = load_dataset()
    metadata = load_metadata()
    filename = metadata.filename
    stats = loader.statistics(df)
    st.info(f"Showing the previously loaded dataset ('{metadata.filename}'). Upload a new file above to replace it, or use 'Clear dataset' to remove it.")

# Checked AFTER upload processing so a file uploaded during this very run
# (which persists immediately, above) makes the button appear right away,
# not only after a subsequent rerun.
if has_dataset() and st.button("Clear dataset"):
    clear_dataset()
    st.session_state.uploader_reset_token += 1
    st.rerun()

if df is not None:
    _render(df, filename, stats)
else:
    st.info("Upload a CSV file to get started.")
