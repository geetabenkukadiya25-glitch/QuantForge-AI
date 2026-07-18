"""Shared Streamlit session-state persistence for the loaded historical dataset.

Centralizes the session_state keys every dashboard page uses to read the
OHLCV DataFrame a user loaded on the Historical Data page, so navigating
to another page -- a full script rerun within the same browser session --
never loses it and a dashboard never needs its own re-upload. This is
presentation-layer state only: no business logic, no engine coupling,
and it never persists to disk -- the dataset lives only as long as the
browser session does, exactly like every other `st.session_state` value
this UI already relies on (e.g. `indicator_registry`, `smc_registry`).
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import streamlit as st

DATASET_KEY = "qf_persisted_dataset"
METADATA_KEY = "qf_persisted_dataset_metadata"


@dataclass(frozen=True)
class DatasetMetadata:
    """Descriptive metadata about the currently persisted dataset."""

    filename: str
    symbol: str | None = None
    timeframe: str | None = None
    statistics: dict[str, Any] = field(default_factory=dict)


def save_dataset(
    data: pd.DataFrame,
    filename: str,
    symbol: str | None = None,
    timeframe: str | None = None,
    statistics: dict[str, Any] | None = None,
) -> None:
    """Persist `data` and its descriptive metadata into session state.

    Overwrites any previously persisted dataset -- loading a new file is
    the one implicit way the old dataset goes away; `clear_dataset()` is
    the only other way.
    """
    st.session_state[DATASET_KEY] = data
    st.session_state[METADATA_KEY] = DatasetMetadata(filename=filename, symbol=symbol or None, timeframe=timeframe, statistics=statistics or {})


def has_dataset() -> bool:
    """Whether a dataset is currently persisted in session state."""
    return st.session_state.get(DATASET_KEY) is not None


def load_dataset() -> pd.DataFrame | None:
    """The currently persisted OHLCV DataFrame, or `None` if nothing has been loaded yet."""
    return st.session_state.get(DATASET_KEY)


def load_metadata() -> DatasetMetadata | None:
    """The currently persisted dataset's metadata, or `None` if nothing has been loaded yet."""
    return st.session_state.get(METADATA_KEY)


def clear_dataset() -> None:
    """Explicitly clear the persisted dataset -- the only way it's ever removed
    other than loading a replacement via `save_dataset()`."""
    st.session_state.pop(DATASET_KEY, None)
    st.session_state.pop(METADATA_KEY, None)


def debug_snapshot() -> dict[str, Any]:
    """A diagnostic snapshot of every session_state key currently set, plus
    the persisted dataset's type/shape/filename/metadata (or their
    absence). Exists so dataset persistence can be verified visually, at
    runtime, in the actual running app -- not just inferred from code."""
    dataset = st.session_state.get(DATASET_KEY)
    metadata = st.session_state.get(METADATA_KEY)
    return {
        "session_state_keys": sorted(str(k) for k in st.session_state.keys()),
        "dataset_key": DATASET_KEY,
        "metadata_key": METADATA_KEY,
        "dataset_present": dataset is not None,
        "dataset_type": type(dataset).__name__ if dataset is not None else None,
        "dataset_shape": tuple(dataset.shape) if dataset is not None else None,
        "metadata": {
            "filename": metadata.filename,
            "symbol": metadata.symbol,
            "timeframe": metadata.timeframe,
            "statistics": metadata.statistics,
        }
        if metadata is not None
        else None,
    }


def render_debug_panel(label: str = "Debug: Session State (dataset persistence)") -> None:
    """Renders `debug_snapshot()` in a collapsed expander. Drop this into
    any page to visually confirm -- in the real running app -- that both
    pages see the exact same session_state keys and dataset."""
    with st.expander(label, expanded=False):
        st.json(debug_snapshot())


def render_debug_banner(container: Any = None) -> None:
    """An always-visible (never collapsed) one-line banner: DATASET FOUND
    YES/NO, DataFrame shape, filename, and every current session_state
    key.

    Pass the `st.empty()` placeholder returned near the top of a page's
    script, then call this again at the END of the script (after any
    upload/save logic has run). Rendering into a reserved placeholder --
    rather than calling this once at the very top -- is required: this
    same script executes top-to-bottom in one rerun, so a banner call
    made before the upload-processing code sees session_state as it was
    BEFORE this run's upload takes effect, not after. Defaults to
    top-level `st` (renders wherever called) if no placeholder is given.
    """
    target = container if container is not None else st
    snap = debug_snapshot()
    found = "YES" if snap["dataset_present"] else "NO"
    shape = snap["dataset_shape"]
    filename = snap["metadata"]["filename"] if snap["metadata"] else None
    message = f"DATASET FOUND = {found} | DataFrame shape = {shape} | Filename = {filename} | Session keys = {snap['session_state_keys']}"
    (target.success if snap["dataset_present"] else target.error)(message)
