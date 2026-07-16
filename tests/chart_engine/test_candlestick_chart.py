"""Tests for CandlestickChart and OHLCChart (rendering + loading)."""

import plotly.graph_objects as go
import pytest

from app.chart_engine.candlestick_chart import CandlestickChart
from app.chart_engine.exceptions import ChartDataError
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.ohlc_chart import OHLCChart


def test_candlestick_build_returns_figure_with_all_candles(hourly_df) -> None:
    fig = CandlestickChart().build(hourly_df)
    assert isinstance(fig, go.Figure)
    assert isinstance(fig.data[0], go.Candlestick)
    assert len(fig.data[0].x) == len(hourly_df)


def test_candlestick_missing_columns_raises(minimal_df) -> None:
    broken = minimal_df.drop(columns=["High"])
    with pytest.raises(ChartDataError):
        CandlestickChart().build(broken)


def test_candlestick_empty_dataframe_raises(minimal_df) -> None:
    with pytest.raises(ChartDataError):
        CandlestickChart().build(minimal_df.iloc[0:0])


def test_candlestick_applies_theme_colors(hourly_df) -> None:
    fig = CandlestickChart().build(hourly_df, ChartConfig(theme="light"))
    assert fig.data[0].increasing.line.color == "#089981"


def test_ohlc_build_returns_figure_with_all_candles(hourly_df) -> None:
    fig = OHLCChart().build(hourly_df)
    assert isinstance(fig.data[0], go.Ohlc)
    assert len(fig.data[0].x) == len(hourly_df)


def test_ohlc_missing_columns_raises(minimal_df) -> None:
    broken = minimal_df.drop(columns=["Close"])
    with pytest.raises(ChartDataError):
        OHLCChart().build(broken)
