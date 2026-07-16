"""Tests for individual drawing tool objects."""

import pandas as pd
import pytest

from app.chart_engine.drawing_objects import (
    Arrow,
    HorizontalLine,
    MeasurementTool,
    Rectangle,
    RiskRewardBox,
    TextLabel,
    TrendLine,
    VerticalLine,
)

T0 = pd.Timestamp("2024-01-01 00:00")
T1 = pd.Timestamp("2024-01-01 04:00")


def test_horizontal_line_shape_and_label() -> None:
    line = HorizontalLine(price=1.1005, label="Pivot")
    shapes = line.to_shapes()
    assert shapes[0]["type"] == "line"
    assert shapes[0]["y0"] == shapes[0]["y1"] == 1.1005
    assert line.to_annotations()[0]["text"] == "Pivot"


def test_horizontal_line_without_label_has_no_annotation() -> None:
    assert HorizontalLine(price=1.1005).to_annotations() == []


def test_vertical_line_shape_uses_iso_timestamp() -> None:
    line = VerticalLine(timestamp=T0)
    shape = line.to_shapes()[0]
    assert shape["x0"] == shape["x1"] == T0.isoformat()


def test_trend_line_shape_coordinates() -> None:
    line = TrendLine(x0=T0, y0=1.10, x1=T1, y1=1.105)
    shape = line.to_shapes()[0]
    assert shape["x0"] == T0.isoformat()
    assert shape["x1"] == T1.isoformat()
    assert shape["y0"] == 1.10
    assert shape["y1"] == 1.105


def test_rectangle_shape_is_rect_type() -> None:
    rect = Rectangle(x0=T0, y0=1.09, x1=T1, y1=1.11)
    assert rect.to_shapes()[0]["type"] == "rect"


def test_text_label_annotation_has_text() -> None:
    label = TextLabel(x=T0, y=1.10, text="Breakout")
    assert label.to_shapes() == []
    assert label.to_annotations()[0]["text"] == "Breakout"


def test_arrow_annotation_has_arrowhead() -> None:
    arrow = Arrow(x0=T0, y0=1.10, x1=T1, y1=1.105)
    annotation = arrow.to_annotations()[0]
    assert annotation["showarrow"] is True
    assert annotation["ax"] == T0.isoformat()


def test_risk_reward_ratio_computed_correctly() -> None:
    box = RiskRewardBox(entry=1.10, stop=1.095, target=1.11, x0=T0, x1=T1)
    assert box.risk_reward_ratio == pytest.approx(2.0)


def test_risk_reward_ratio_zero_when_no_risk() -> None:
    box = RiskRewardBox(entry=1.10, stop=1.10, target=1.11, x0=T0, x1=T1)
    assert box.risk_reward_ratio == 0.0


def test_risk_reward_box_has_two_shapes() -> None:
    box = RiskRewardBox(entry=1.10, stop=1.095, target=1.11, x0=T0, x1=T1)
    assert len(box.to_shapes()) == 2


def test_measurement_tool_price_delta() -> None:
    tool = MeasurementTool(x0=T0, y0=1.10, x1=T1, y1=1.105)
    assert tool.price_delta == pytest.approx(0.005)
    assert tool.time_delta == pd.Timedelta(hours=4)
