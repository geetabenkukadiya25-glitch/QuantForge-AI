"""Side-by-side multi-timeframe candlestick view."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.chart_engine.candlestick_chart import CandlestickChart
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.schema import validate_ohlcv
from app.chart_engine.themes import get_theme
from app.chart_engine.timeframe import resample_ohlcv


class MultiTimeframeChart:
    """Builds a stacked figure showing the same data at several timeframes."""

    def __init__(self, candlestick_chart: CandlestickChart | None = None) -> None:
        self._candlestick = candlestick_chart or CandlestickChart()

    def build(
        self,
        df: pd.DataFrame,
        timeframes: list[str],
        config: ChartConfig | None = None,
    ) -> go.Figure:
        """Return a figure with one candlestick subplot per timeframe in `timeframes`.

        Raises:
            ChartDataError: if `df` lacks the required OHLC columns.
            ChartEngineError: if a timeframe label is unrecognized.
        """
        validate_ohlcv(df)
        if not timeframes:
            raise ValueError("timeframes must be a non-empty list")

        config = config or ChartConfig()
        theme = get_theme(config.theme)

        fig = make_subplots(
            rows=len(timeframes),
            cols=1,
            shared_xaxes=False,
            subplot_titles=timeframes,
            vertical_spacing=0.06 if len(timeframes) > 1 else 0,
        )

        for i, timeframe in enumerate(timeframes, start=1):
            resampled = resample_ohlcv(df, timeframe)
            self._candlestick.add_trace(fig, resampled, theme, row=i, col=1)
            fig.update_xaxes(rangeslider_visible=False, gridcolor=theme.grid, row=i, col=1)
            fig.update_yaxes(gridcolor=theme.grid, row=i, col=1)

        fig.update_layout(
            title=config.title,
            height=max(config.resolved_height, 250 * len(timeframes)),
            plot_bgcolor=theme.background,
            paper_bgcolor=theme.background,
            font=dict(color=theme.text),
            showlegend=False,
            margin=dict(l=40, r=40, t=40, b=20),
        )
        return fig
