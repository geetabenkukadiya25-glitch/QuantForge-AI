"""Shared Plotly layout application for every chart class.

Centralizes theme colors, crosshair (spike lines), drag mode, and
autoscale so `CandlestickChart`, `OHLCChart`, `VolumeChart`, and
`ChartEngine` all render with consistent, config-driven styling.
"""

import plotly.graph_objects as go

from app.chart_engine.layout_config import ChartConfig
from app.chart_engine.themes import ChartTheme, get_theme


def apply_layout(fig: go.Figure, config: ChartConfig, theme: ChartTheme | None = None) -> go.Figure:
    """Apply `config`'s theme/interaction settings to `fig` in place, and return it."""
    theme = theme or get_theme(config.theme)

    fig.update_layout(
        title=config.title,
        height=config.resolved_height,
        width=config.width,
        plot_bgcolor=theme.background,
        paper_bgcolor=theme.background,
        font=dict(color=theme.text),
        dragmode=config.dragmode,
        hovermode="x" if config.show_crosshair else "closest",
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=40, t=40 if config.title else 20, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )

    fig.update_xaxes(
        gridcolor=theme.grid,
        showspikes=config.show_crosshair,
        spikemode="across",
        spikesnap="cursor",
        spikecolor=theme.crosshair,
        spikethickness=1,
    )
    fig.update_yaxes(
        gridcolor=theme.grid,
        showspikes=config.show_crosshair,
        spikemode="across",
        spikecolor=theme.crosshair,
        spikethickness=1,
        autorange=config.autoscale,
        fixedrange=False,
    )
    return fig
