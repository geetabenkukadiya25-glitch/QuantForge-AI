"""Tests for SessionOverlay."""

import pandas as pd
import plotly.graph_objects as go

from app.chart_engine.sessions import SessionOverlay


def test_active_session_tokyo() -> None:
    overlay = SessionOverlay()
    # 07:00 UTC overlaps Tokyo (00-09) and London (07-16); Tokyo is checked
    # first, matching real forex session overlap behavior.
    assert overlay.active_session(pd.Timestamp("2024-01-01 07:00")) == "Tokyo"


def test_active_session_london() -> None:
    overlay = SessionOverlay()
    assert overlay.active_session(pd.Timestamp("2024-01-01 10:00")) == "London"


def test_active_session_new_york() -> None:
    overlay = SessionOverlay()
    assert overlay.active_session(pd.Timestamp("2024-01-01 18:00")) == "New York"


def test_active_session_sydney_wraps_midnight() -> None:
    overlay = SessionOverlay()
    assert overlay.active_session(pd.Timestamp("2024-01-01 23:00")) == "Sydney"
    assert overlay.active_session(pd.Timestamp("2024-01-01 02:00")) == "Sydney"


def test_add_to_figure_adds_vrect_shapes(hourly_df) -> None:
    fig = go.Figure()
    SessionOverlay().add_to_figure(fig, hourly_df)
    assert len(fig.layout.shapes) > 0


def test_add_to_figure_caps_days(hourly_df) -> None:
    fig_uncapped = go.Figure()
    SessionOverlay().add_to_figure(fig_uncapped, hourly_df, max_days=100)

    fig_capped = go.Figure()
    SessionOverlay().add_to_figure(fig_capped, hourly_df, max_days=1)

    assert len(fig_capped.layout.shapes) < len(fig_uncapped.layout.shapes)


def test_add_to_figure_on_empty_dataframe_noop(minimal_df) -> None:
    fig = go.Figure()
    SessionOverlay().add_to_figure(fig, minimal_df.iloc[0:0])
    assert len(fig.layout.shapes) == 0
