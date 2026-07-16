"""Tests for the ChartEngine facade: rendering, config, drawings, sessions."""

import pytest

from app.chart_engine.chart_engine import ChartEngine
from app.chart_engine.drawing_manager import DrawingManager
from app.chart_engine.drawing_objects import HorizontalLine, VerticalLine
from app.chart_engine.exceptions import ChartDataError, ChartEngineError
from app.chart_engine.layout_config import ChartConfig


def test_render_default_has_price_and_volume_rows(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df)
    assert len(fig.data) == 2  # candlestick + volume


def test_render_without_volume_has_one_trace(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, config=ChartConfig(show_volume=False))
    assert len(fig.data) == 1


def test_render_missing_volume_column_skips_volume_row(minimal_df) -> None:
    fig = ChartEngine().render(minimal_df)
    assert len(fig.data) == 1


def test_render_ohlc_chart_type(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, chart_type="ohlc", config=ChartConfig(show_volume=False))
    assert fig.data[0].type == "ohlc"


def test_render_unknown_chart_type_raises(hourly_df) -> None:
    with pytest.raises(ChartEngineError):
        ChartEngine().render(hourly_df, chart_type="line")


def test_render_missing_columns_raises(minimal_df) -> None:
    broken = minimal_df.drop(columns=["Open"])
    with pytest.raises(ChartDataError):
        ChartEngine().render(broken)


def test_render_dragmode_reflects_config(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, config=ChartConfig(dragmode="zoom"))
    assert fig.layout.dragmode == "zoom"


def test_render_autoscale_sets_yaxis_autorange(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, config=ChartConfig(autoscale=True))
    assert fig.layout.yaxis.autorange is True
    assert fig.layout.yaxis.fixedrange is False


def test_render_crosshair_enables_spikes(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, config=ChartConfig(show_crosshair=True))
    assert fig.layout.xaxis.showspikes is True


def test_render_with_drawing_list_adds_shapes(hourly_df) -> None:
    drawings = [HorizontalLine(price=1.1005), VerticalLine(timestamp=hourly_df["Datetime"].iloc[5])]
    fig = ChartEngine().render(hourly_df, drawings=drawings)
    assert len(fig.layout.shapes) == 2


def test_render_with_drawing_manager_adds_shapes(hourly_df) -> None:
    manager = DrawingManager()
    manager.add(HorizontalLine(price=1.1005))
    fig = ChartEngine().render(hourly_df, drawings=manager)
    assert len(fig.layout.shapes) == 1


def test_render_with_sessions_adds_vrect_shapes(hourly_df) -> None:
    fig = ChartEngine().render(hourly_df, show_sessions=True)
    assert len(fig.layout.shapes) > 0


def test_render_fullscreen_increases_height(hourly_df) -> None:
    normal = ChartEngine().render(hourly_df, config=ChartConfig(fullscreen=False))
    full = ChartEngine().render(hourly_df, config=ChartConfig(fullscreen=True))
    assert full.layout.height > normal.layout.height
