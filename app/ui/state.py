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
