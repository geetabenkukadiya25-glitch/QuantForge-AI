"""Tests for MultiTimeframeChart (timeframe switch / multi-panel view)."""

import pytest

from app.chart_engine.exceptions import ChartDataError
from app.chart_engine.multi_timeframe_chart import MultiTimeframeChart


def test_build_creates_one_trace_per_timeframe(hourly_df) -> None:
    fig = MultiTimeframeChart().build(hourly_df, ["H1", "H4", "D1"])
    assert len(fig.data) == 3


def test_build_empty_timeframes_raises(hourly_df) -> None:
    with pytest.raises(ValueError):
        MultiTimeframeChart().build(hourly_df, [])


def test_build_missing_columns_raises(minimal_df) -> None:
    broken = minimal_df.drop(columns=["Low"])
    with pytest.raises(ChartDataError):
        MultiTimeframeChart().build(broken, ["H1"])


def test_build_single_timeframe_matches_raw_candlestick(hourly_df) -> None:
    fig = MultiTimeframeChart().build(hourly_df, ["H1"])
    assert len(fig.data[0].x) == len(hourly_df)
