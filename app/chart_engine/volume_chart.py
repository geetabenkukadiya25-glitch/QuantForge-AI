"""Standalone and subplot volume bar rendering."""

import pandas as pd
import plotly.graph_objects as go

from app.chart_engine.exceptions import ChartDataError
from app.chart_engine.layout import apply_layout
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.schema import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.chart_engine.themes import get_theme


class VolumeChart:
    """Builds volume bars, colored by candle direction."""

    def build(self, df: pd.DataFrame, config: ChartConfig | None = None) -> go.Figure:
        """Return a standalone volume-bar figure for `df`.

        Raises:
            ChartDataError: if `df` lacks a `Volume` column.
        """
        if VOLUME_COL not in df.columns:
            raise ChartDataError(f"Cannot chart volume: missing column '{VOLUME_COL}'")
        config = config or ChartConfig()
        theme = get_theme(config.theme)

        fig = go.Figure()
        self.add_trace(fig, df, theme)
        apply_layout(fig, config, theme)
        return fig

    @staticmethod
    def add_trace(fig: go.Figure, df: pd.DataFrame, theme, row: int | None = None, col: int | None = None) -> None:
        """Add a volume bar trace for `df` to an existing figure/subplot."""
        open_, close = df[OHLC_COLS[0]], df[OHLC_COLS[3]]
        colors = [theme.up if c >= o else theme.down for o, c in zip(open_, close)]

        trace = go.Bar(
            x=df[DATETIME_COL],
            y=df[VOLUME_COL],
            marker_color=colors,
            name="Volume",
        )
        if row is not None and col is not None:
            fig.add_trace(trace, row=row, col=col)
        else:
            fig.add_trace(trace)
