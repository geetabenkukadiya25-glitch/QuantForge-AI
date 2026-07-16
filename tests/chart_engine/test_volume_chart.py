"""Tests for VolumeChart."""

import plotly.graph_objects as go
import pytest

from app.chart_engine.exceptions import ChartDataError
from app.chart_engine.volume_chart import VolumeChart


def test_volume_build_returns_bar_trace(hourly_df) -> None:
    fig = VolumeChart().build(hourly_df)
    assert isinstance(fig.data[0], go.Bar)
    assert len(fig.data[0].y) == len(hourly_df)


def test_volume_missing_column_raises(minimal_df) -> None:
    with pytest.raises(ChartDataError):
        VolumeChart().build(minimal_df)


def test_volume_colors_reflect_candle_direction(hourly_df) -> None:
    fig = VolumeChart().build(hourly_df)
    colors = fig.data[0].marker.color
    for i in range(len(hourly_df)):
        expected_up = hourly_df["Close"].iloc[i] >= hourly_df["Open"].iloc[i]
        assert (colors[i] == "#26A69A") == expected_up
