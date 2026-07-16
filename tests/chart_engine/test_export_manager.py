"""Tests for ExportManager (PNG/SVG/HTML export)."""

import plotly.graph_objects as go
import pytest

from app.chart_engine.candlestick_chart import CandlestickChart
from app.chart_engine.export_manager import ExportManager


@pytest.fixture
def figure(hourly_df) -> go.Figure:
    return CandlestickChart().build(hourly_df)


def test_export_to_html(figure, tmp_path) -> None:
    out_path = tmp_path / "chart.html"
    result = ExportManager().to_html(figure, out_path)
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert "plotly" in out_path.read_text(encoding="utf-8").lower()


def test_export_to_png(figure, tmp_path) -> None:
    out_path = tmp_path / "chart.png"
    ExportManager().to_png(figure, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_export_to_svg(figure, tmp_path) -> None:
    out_path = tmp_path / "chart.svg"
    ExportManager().to_svg(figure, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_export_creates_parent_directories(figure, tmp_path) -> None:
    out_path = tmp_path / "nested" / "dir" / "chart.html"
    ExportManager().to_html(figure, out_path)
    assert out_path.exists()
