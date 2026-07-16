"""Top-level facade composing every chart_engine capability.

`ChartEngine.render` is the one call most consumers (the Streamlit page,
future indicator/strategy overlays) need: candlestick or OHLC price pane,
optional volume subplot, optional session bands, optional drawings.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.chart_engine.candlestick_chart import CandlestickChart
from app.chart_engine.drawing_manager import DrawingManager
from app.chart_engine.drawing_objects import DrawingObject
from app.chart_engine.exceptions import ChartEngineError
from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.multi_timeframe_chart import MultiTimeframeChart
from app.chart_engine.ohlc_chart import OHLCChart
from app.chart_engine.schema import VOLUME_COL, validate_ohlcv
from app.chart_engine.sessions import SessionOverlay
from app.chart_engine.themes import get_theme
from app.chart_engine.volume_chart import VolumeChart

CHART_TYPES = {"candlestick": CandlestickChart, "ohlc": OHLCChart}


class ChartEngine:
    """Composes price/volume/session/drawing rendering into one figure."""

    def __init__(
        self,
        candlestick_chart: CandlestickChart | None = None,
        ohlc_chart: OHLCChart | None = None,
        volume_chart: VolumeChart | None = None,
        session_overlay: SessionOverlay | None = None,
        multi_timeframe_chart: MultiTimeframeChart | None = None,
    ) -> None:
        self._candlestick = candlestick_chart or CandlestickChart()
        self._ohlc = ohlc_chart or OHLCChart()
        self._volume = volume_chart or VolumeChart()
        self._sessions = session_overlay or SessionOverlay()
        self._multi_timeframe = multi_timeframe_chart or MultiTimeframeChart(self._candlestick)

    def render(
        self,
        df: pd.DataFrame,
        config: ChartConfig | None = None,
        chart_type: str = "candlestick",
        show_sessions: bool = False,
        drawings: list[DrawingObject] | DrawingManager | None = None,
    ) -> go.Figure:
        """Render `df` as a full chart: price pane (+ optional volume/sessions/drawings).

        Args:
            df: standard-schema OHLCV DataFrame (see `chart_engine.schema`).
            config: display/interaction settings; defaults to `ChartConfig()`.
            chart_type: "candlestick" or "ohlc".
            show_sessions: overlay market session background bands.
            drawings: a `DrawingManager`, or a plain list of `DrawingObject`s.

        Raises:
            ChartDataError: if `df` lacks required OHLC columns.
            ChartEngineError: if `chart_type` is not recognized.
        """
        validate_ohlcv(df)
        price_chart_cls = CHART_TYPES.get(chart_type)
        if price_chart_cls is None:
            raise ChartEngineError(
                f"Unknown chart_type: {chart_type!r}. Available: {list(CHART_TYPES)}"
            )
        price_chart = self._candlestick if chart_type == "candlestick" else self._ohlc

        config = config or ChartConfig()
        theme = get_theme(config.theme)
        show_volume = config.show_volume and VOLUME_COL in df.columns

        if show_volume:
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                row_heights=[0.75, 0.25],
                vertical_spacing=0.03,
            )
            price_chart.add_trace(fig, df, theme, row=1, col=1)
            self._volume.add_trace(fig, df, theme, row=2, col=1)
        else:
            fig = make_subplots(rows=1, cols=1)
            price_chart.add_trace(fig, df, theme, row=1, col=1)

        self._apply_full_layout(fig, config, theme, show_volume)

        if show_sessions:
            self._sessions.add_to_figure(fig, df, config=config, row=1, col=1)

        if drawings is not None:
            manager = drawings if isinstance(drawings, DrawingManager) else DrawingManager()
            if not isinstance(drawings, DrawingManager):
                for drawing in drawings:
                    manager.add(drawing)
            manager.render(fig)

        return fig

    def render_multi_timeframe(
        self,
        df: pd.DataFrame,
        timeframes: list[str],
        config: ChartConfig | None = None,
    ) -> go.Figure:
        """Render `df` as stacked candlestick subplots, one per timeframe."""
        return self._multi_timeframe.build(df, timeframes, config)

    @staticmethod
    def _apply_full_layout(
        fig: go.Figure, config: ChartConfig, theme, show_volume: bool
    ) -> None:
        fig.update_layout(
            title=config.title,
            height=config.resolved_height,
            width=config.width,
            plot_bgcolor=theme.background,
            paper_bgcolor=theme.background,
            font=dict(color=theme.text),
            dragmode=config.dragmode,
            hovermode="x" if config.show_crosshair else "closest",
            showlegend=False,
            margin=dict(l=40, r=40, t=40 if config.title else 20, b=20),
        )
        rows = [1, 2] if show_volume else [1]
        for row in rows:
            fig.update_xaxes(
                gridcolor=theme.grid,
                showspikes=config.show_crosshair,
                spikemode="across",
                spikesnap="cursor",
                spikecolor=theme.crosshair,
                spikethickness=1,
                rangeslider_visible=False,
                row=row,
                col=1,
            )
            fig.update_yaxes(
                gridcolor=theme.grid,
                showspikes=config.show_crosshair,
                spikemode="across",
                spikecolor=theme.crosshair,
                spikethickness=1,
                autorange=config.autoscale,
                fixedrange=False,
                row=row,
                col=1,
            )
