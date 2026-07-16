"""Helpers for converting pandas frequency aliases to `Timedelta` values."""

import pandas as pd

_REFERENCE_TIMESTAMP = pd.Timestamp("2000-01-01")


def freq_to_timedelta(freq: str) -> pd.Timedelta:
    """Return the approximate duration of a pandas frequency alias.

    `pd.Timedelta` can't be constructed directly from calendar-based
    offsets (e.g. "1MS"), so this measures the offset's effect on a fixed
    reference timestamp instead.
    """
    offset = pd.tseries.frequencies.to_offset(freq)
    return (_REFERENCE_TIMESTAMP + offset) - _REFERENCE_TIMESTAMP
