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

import streamlit as st

from app.data_engine import (
    CSVFormatError,
    DataCleaner,
    DataLoader,
    generate_quality_report,
)
from app.dataset_manager import DatasetManager
from app.ui.components import (
    ToolbarAction,
    render_command_bar,
    render_info_card,
    render_notification_center,
    render_shell,
    render_status_bar,
    render_toolbar,
)
from app.ui.state import clear_dataset, has_dataset, load_dataset, load_metadata, render_debug_banner, render_debug_panel, save_dataset

st.set_page_config(page_title="Historical Data - QuantForge AI", page_icon="📈", layout="wide")

# Reserved here (top of page) but filled at the END of the script, after
# any upload/save this run has processed -- see render_debug_banner's
# docstring for why filling it here-and-now would show stale data.
banner_slot = st.empty()

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Historical Data")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Historical Data")
st.caption("Load, validate, and inspect historical OHLCV data. The loaded dataset stays available to every other dashboard page.")

loader = DataLoader()
cleaner = DataCleaner()

if "uploader_reset_token" not in st.session_state:
    st.session_state.uploader_reset_token = 0

explorer_col, workspace_col, info_col = render_shell()

# -----------------------------------------------------------------------
# Explorer (left) -- the page's existing input widgets, unchanged (same
# variables, keys, order), just relocated out of the old top-of-body flow.
# -----------------------------------------------------------------------

with explorer_col:
    st.subheader("Explorer")
    # Keyed off a token that "Clear dataset" bumps below -- otherwise
    # clearing the persisted dataset while the file_uploader widget still
    # holds its previous file would just re-persist that same file on the
    # very next rerun, silently undoing the clear.
    uploaded_file = st.file_uploader(
        "Upload a CSV file (standard or MT5 export format)", type=["csv"], key=f"historical_data_uploader_{st.session_state.uploader_reset_token}"
    )
    clean_on_load = st.checkbox("Clean on load (sort, de-duplicate, drop unparseable rows)", value=True)
    symbol_label = st.text_input("Symbol (optional, for reference only)", value="")
    render_debug_panel()

df, filename, stats = None, None, None
dataset_manager = DatasetManager()

if uploaded_file is not None:
    # Every upload becomes a managed `DatasetManager` asset (deduped by
    # content hash) instead of a throwaway temp file -- this is now the
    # single source of truth every dashboard's dataset picker reads from;
    # the resolved DataFrame is still handed to `save_dataset()` exactly
    # as before, so the rest of this page (and every page reading the
    # shared session slot) is unchanged.
    try:
        record = dataset_manager.import_dataset_from_bytes(uploaded_file.getvalue(), filename=uploaded_file.name, clean=clean_on_load)
    except CSVFormatError as exc:
        st.error(f"Could not load file: {exc}")
    else:
        dataset_manager.record_used(record.id)
        df = dataset_manager.load_dataframe(record.id)
        filename = record.filename
        stats = loader.statistics(df)
        save_dataset(df, filename=filename, symbol=symbol_label or record.symbol, timeframe=record.timeframe or stats["detected_timeframe"], statistics=stats)

elif has_dataset():
    df = load_dataset()
    metadata = load_metadata()
    filename = metadata.filename
    stats = loader.statistics(df)

# -----------------------------------------------------------------------
# Workspace (center) -- toolbar + tabs replacing the old linear section
# stack (Preview / Statistics / Quality Report). Every value rendered
# below is the exact same `df`/`filename`/`stats`/`report` this page
# already computed above.
# -----------------------------------------------------------------------

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("🗑 Clear", "clear", enabled=has_dataset(), disabled_reason=None if has_dataset() else "No dataset loaded."),
            ToolbarAction("💾 Export", "export", enabled=False, disabled_reason="Export is not implemented for Historical Data in this phase."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("clear") and has_dataset():
        clear_dataset()
        st.session_state.uploader_reset_token += 1
        st.rerun()

    if df is None:
        st.info("Upload a CSV file to get started.")
    else:
        if uploaded_file is not None:
            st.success(f"Loaded {len(df):,} candles from '{filename}'.")
        else:
            st.info(f"Showing the previously loaded dataset ('{filename}'). Upload a new file in the Explorer to replace it, or use 'Clear' to remove it.")

        overview_tab, preview_tab, stats_tab, quality_tab = st.tabs(["Overview", "Preview", "Statistics", "Quality Report"])

        with overview_tab:
            cols = st.columns(4)
            cols[0].metric("Candles", f"{stats['num_candles']:,}")
            cols[1].metric("Detected timeframe", stats["detected_timeframe"] or "—")
            cols[2].metric("Missing candles", f"{stats['missing_candles']:,}")
            cols[3].metric("Duplicate candles", f"{stats['duplicate_candles']:,}")
            st.write(
                f"Date range: **{stats['date_range_start']}** → **{stats['date_range_end']}**  \n"
                f"Memory usage: **{stats['memory_usage_bytes'] / 1024:.1f} KB**"
            )

        with preview_tab:
            head_col, tail_col = st.columns(2)
            with head_col:
                st.caption("First rows")
                st.dataframe(loader.preview_head(df), use_container_width=True)
            with tail_col:
                st.caption("Last rows")
                st.dataframe(loader.preview_tail(df), use_container_width=True)

        with stats_tab:
            cols = st.columns(4)
            cols[0].metric("Candles", f"{stats['num_candles']:,}")
            cols[1].metric("Detected timeframe", stats["detected_timeframe"] or "—")
            cols[2].metric("Missing candles", f"{stats['missing_candles']:,}")
            cols[3].metric("Duplicate candles", f"{stats['duplicate_candles']:,}")

        with quality_tab:
            report = generate_quality_report(df)
            report_dict = {key: str(value) for key, value in report.to_dict().items()}
            st.json(report_dict, expanded=False)

# -----------------------------------------------------------------------
# Information (right) -- dataset metadata card, sourced from the same
# `stats`/`filename` this page already computed.
# -----------------------------------------------------------------------

with info_col:
    st.subheader("Dataset Information")
    if df is None:
        st.caption("Nothing loaded yet.")
    else:
        render_info_card(
            "Dataset",
            [
                ("Filename", filename),
                ("Candles", f"{stats['num_candles']:,}"),
                ("Timeframe", stats["detected_timeframe"] or "—"),
                ("Symbol", symbol_label or "—"),
            ],
        )
        render_info_card(
            "Quality",
            [
                ("Missing candles", f"{stats['missing_candles']:,}"),
                ("Duplicate candles", f"{stats['duplicate_candles']:,}"),
            ],
        )

# Checked AFTER upload processing so a file uploaded during this very run
# (which persists immediately, above) reflects right away, not only after
# a subsequent rerun.
render_debug_banner(banner_slot)

render_status_bar(
    module="Historical Data",
    strategy_status="—",
    validation_status="—",
    execution_status="Loaded" if df is not None else "Ready",
)
