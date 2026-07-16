"""Tests for DrawingManager."""

import plotly.graph_objects as go
import pytest

from app.chart_engine.drawing_manager import DrawingManager
from app.chart_engine.drawing_objects import HorizontalLine, TextLabel


def test_add_returns_index() -> None:
    manager = DrawingManager()
    idx = manager.add(HorizontalLine(price=1.10))
    assert idx == 0
    assert len(manager.list()) == 1


def test_remove_deletes_drawing() -> None:
    manager = DrawingManager()
    manager.add(HorizontalLine(price=1.10))
    manager.remove(0)
    assert manager.list() == []


def test_remove_invalid_index_raises() -> None:
    manager = DrawingManager()
    with pytest.raises(IndexError):
        manager.remove(0)


def test_clear_removes_all_drawings() -> None:
    manager = DrawingManager()
    manager.add(HorizontalLine(price=1.10))
    manager.add(HorizontalLine(price=1.11))
    manager.clear()
    assert manager.list() == []


def test_render_applies_shapes_and_annotations_to_bare_figure() -> None:
    manager = DrawingManager()
    manager.add(HorizontalLine(price=1.10, label="Level"))
    manager.add(TextLabel(x="2024-01-01T00:00:00", y=1.10, text="Note"))

    fig = go.Figure()
    manager.render(fig)

    assert len(fig.layout.shapes) == 1
    assert len(fig.layout.annotations) == 2  # HorizontalLine label + TextLabel


def test_render_on_bare_figure_is_independent_of_chart_engine() -> None:
    manager = DrawingManager()
    manager.add(HorizontalLine(price=1.10))
    fig = manager.render(go.Figure())
    assert isinstance(fig, go.Figure)
