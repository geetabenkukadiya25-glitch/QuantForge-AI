"""Shared, reusable primitives for Smart Money detectors.

Several detectors need the same underlying computation (swing point
scanning, rolling range, previous-calendar-period extremes) with
different parameters. Centralizing them here avoids duplicating pandas
logic across detector modules, per `PROJECT_VISION.md`'s "no duplicate
code" rule.
"""

import pandas as pd

from app.smart_money_engine.schema import DATETIME_COL


def find_swing_highs(data: pd.DataFrame, left_bars: int, right_bars: int) -> list[int]:
    """Return positional indices where `High` is the strict max of its `[-left, +right]` window."""
    high = data["High"].to_numpy()
    n = len(high)
    swings: list[int] = []
    for i in range(left_bars, n - right_bars):
        window = high[i - left_bars : i + right_bars + 1]
        window_max = window.max()
        if high[i] == window_max and (window == window_max).sum() == 1:
            swings.append(i)
    return swings


def find_swing_lows(data: pd.DataFrame, left_bars: int, right_bars: int) -> list[int]:
    """Return positional indices where `Low` is the strict min of its `[-left, +right]` window."""
    low = data["Low"].to_numpy()
    n = len(low)
    swings: list[int] = []
    for i in range(left_bars, n - right_bars):
        window = low[i - left_bars : i + right_bars + 1]
        window_min = window.min()
        if low[i] == window_min and (window == window_min).sum() == 1:
            swings.append(i)
    return swings


def average_range(data: pd.DataFrame, window: int) -> pd.Series:
    """Rolling mean of the High-Low range, used as a volatility baseline."""
    return (data["High"] - data["Low"]).rolling(window).mean()


def iso_at(data: pd.DataFrame, index: int) -> str:
    """ISO-format the `Datetime` value at a positional index."""
    value = data[DATETIME_COL].iloc[index]
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def previous_period_extreme(
    data: pd.DataFrame, freq: str, column: str, agg: str
) -> list[tuple[int, float]]:
    """For each calendar period after the first, pair its first row's index with
    the *previous* period's `column` extreme (`agg` = "max" or "min").

    Args:
        freq: "D" (day), "W" (ISO week), or "M" (calendar month).
    """
    dt = data[DATETIME_COL]
    if freq == "D":
        period_key = dt.dt.date.astype(str)
    elif freq == "W":
        iso = dt.dt.isocalendar()
        period_key = iso.year.astype(str) + "-W" + iso.week.astype(str)
    elif freq == "M":
        period_key = dt.dt.to_period("M").astype(str)
    else:
        raise ValueError(f"Unsupported freq: {freq!r} (expected 'D', 'W', or 'M')")

    period_key = period_key.reset_index(drop=True)
    values = data[column].reset_index(drop=True)

    first_index_by_period: dict[str, int] = {}
    extreme_by_period: dict[str, float] = {}
    order: list[str] = []
    for i, period in enumerate(period_key):
        if period not in first_index_by_period:
            first_index_by_period[period] = i
            order.append(period)
        value = float(values[i])
        current = extreme_by_period.get(period)
        if current is None:
            extreme_by_period[period] = value
        else:
            extreme_by_period[period] = max(current, value) if agg == "max" else min(current, value)

    results: list[tuple[int, float]] = []
    for i in range(1, len(order)):
        current_period, previous_period = order[i], order[i - 1]
        results.append((first_index_by_period[current_period], extreme_by_period[previous_period]))
    return results
