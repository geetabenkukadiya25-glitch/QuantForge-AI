"""Standalone candlestick chart rendering."""

import pandas as pd
import plotly.graph_objects as go

from app.chart_engine.layout import apply_layout
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.schema import DATETIME_COL, OHLC_COLS, validate_ohlcv
from app.chart_engine.themes import get_theme


class CandlestickChart:
    """Builds a professional candlestick `go.Figure` from OHLCV data."""

    def build(self, df: pd.DataFrame, config: ChartConfig | None = None) -> go.Figure:
        """Return a standalone candlestick figure for `df`.

        Raises:
            ChartDataError: if `df` lacks the required OHLC columns.
        """
        validate_ohlcv(df)
        config = config or ChartConfig()
        theme = get_theme(config.theme)

        fig = go.Figure()
        self.add_trace(fig, df, theme)
        apply_layout(fig, config, theme)
        return fig

    @staticmethod
    def add_trace(fig: go.Figure, df: pd.DataFrame, theme, row: int | None = None, col: int | None = None) -> None:
        """Add a candlestick trace for `df` to an existing figure/subplot."""
        trace = go.Candlestick(
            x=df[DATETIME_COL],
            open=df[OHLC_COLS[0]],
            high=df[OHLC_COLS[1]],
            low=df[OHLC_COLS[2]],
            close=df[OHLC_COLS[3]],
            increasing_line_color=theme.up,
            decreasing_line_color=theme.down,
            increasing_fillcolor=theme.up,
            decreasing_fillcolor=theme.down,
            name="Price",
        )
        if row is not None and col is not None:
            fig.add_trace(trace, row=row, col=col)
        else:
            fig.add_trace(trace)
