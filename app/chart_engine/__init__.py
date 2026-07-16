"""Professional chart visualization engine.

Renders candlestick/OHLC/volume charts, multi-timeframe views, market
session overlays, drawing tools, and export to PNG/SVG/HTML -- given any
DataFrame following the standard OHLCV schema (see `chart_engine.schema`).

Deliberately independent from `app.data_engine`: no module in this
package imports it. This module contains no indicators, no strategy
logic, no AI, and no backtesting, per the Phase 3 scope.
"""

from app.chart_engine.candlestick_chart import CandlestickChart
from app.chart_engine.chart_engine import ChartEngine
from app.chart_engine.drawing_manager import DrawingManager
from app.chart_engine.drawing_objects import (
    Arrow,
    DrawingObject,
    HorizontalLine,
    MeasurementTool,
    Rectangle,
    RiskRewardBox,
    TextLabel,
    TrendLine,
    VerticalLine,
)
from app.chart_engine.exceptions import ChartDataError, ChartEngineError, DrawingError, ExportError
from app.chart_engine.export_manager import ExportManager
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.multi_timeframe_chart import MultiTimeframeChart
from app.chart_engine.ohlc_chart import OHLCChart
from app.chart_engine.sessions import MarketSession, SessionOverlay
from app.chart_engine.themes import ChartTheme, get_theme
from app.chart_engine.timeframe import TIMEFRAMES, resample_ohlcv
from app.chart_engine.volume_chart import VolumeChart

__all__ = [
    "ChartEngine",
    "ChartConfig",
    "CandlestickChart",
    "OHLCChart",
    "VolumeChart",
    "MultiTimeframeChart",
    "SessionOverlay",
    "MarketSession",
    "DrawingManager",
    "DrawingObject",
    "HorizontalLine",
    "VerticalLine",
    "TrendLine",
    "Rectangle",
    "TextLabel",
    "Arrow",
    "RiskRewardBox",
    "MeasurementTool",
    "ExportManager",
    "ChartTheme",
    "get_theme",
    "TIMEFRAMES",
    "resample_ohlcv",
    "ChartEngineError",
    "ChartDataError",
    "DrawingError",
    "ExportError",
]
