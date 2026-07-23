"""Shared dataset-sourcing component (Phase 18.6) -- the ONE place every
dashboard resolves its working `pd.DataFrame` from, replacing each page's
previous local `file_uploader` -> `tempfile` -> `DataLoader.load_csv`
block. Every dataset resolved here is a managed `DatasetManager` asset
(uploads are registered, with automatic dedup by content hash) -- no page
using this component ever scans a folder or loads a CSV on its own.
"""

import streamlit as st

from app.data_engine import CSVFormatError
from app.dataset_manager import DatasetManager, DatasetRecord

_UPLOAD_OPTION = "➕ Upload new dataset"


def _label_for(record: DatasetRecord) -> str:
    star = "⭐ " if record.favorite else ""
    return f"{star}{record.display_name} ({record.symbol or '—'} / {record.timeframe or '—'})"


def render_dataset_picker(page_key: str, container=None, manager: DatasetManager | None = None, catalog=None):
    """Render a selectbox of managed datasets plus an upload fallback.
    Returns `(dataframe, record)`, or `(None, None)` if nothing is
    resolved yet on this run (caller should `st.stop()` in that case,
    same as the old `if uploaded_file is None: st.stop()` guard).

    `catalog` (Phase 17.5) defaults to the real, process-wide
    `DataCatalog()` -- overridable the same way `manager` already is, so
    tests can inject an isolated instance instead of touching real disk."""
    target = container if container is not None else st
    manager = manager or DatasetManager()

    entries = manager.list_entries(archived=False)
    options = [_UPLOAD_OPTION] + [_label_for(e) for e in entries]
    choice = target.selectbox("Dataset", options, key=f"dsp_{page_key}_choice")

    if choice == _UPLOAD_OPTION:
        uploaded = target.file_uploader(
            "Upload a CSV file (standard or MT5 export format)", type=["csv"], key=f"dsp_{page_key}_uploader"
        )
        if uploaded is None:
            return None, None
        data = uploaded.getvalue()
        try:
            record = manager.import_dataset_from_bytes(data, filename=uploaded.name)
        except CSVFormatError as exc:
            target.error(f"Could not load dataset: {exc}")
            return None, None
    else:
        record = entries[options.index(choice) - 1]

    manager.record_used(record.id)
    df = manager.load_dataframe(record.id)

    try:
        from app.data_catalog import DataCatalog

        (catalog or DataCatalog()).record_usage_context(page_key, record.id)
    except Exception:  # noqa: BLE001 -- catalog usage tracking must never break dataset loading
        pass

    return df, record
