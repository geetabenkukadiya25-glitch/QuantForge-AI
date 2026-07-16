"""Market session overlays (Sydney, Tokyo, London, New York).

Session windows are approximate, fixed UTC hours (DST is not modeled) --
good enough for visual context, not for precision session-boundary logic.
"""

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from app.chart_engine.schema import DATETIME_COL
from app.chart_engine.themes import ChartTheme, get_theme


@dataclass(frozen=True)
class MarketSession:
    """A trading session's approximate UTC open/close hour (0-24, may wrap midnight)."""

    name: str
    start_hour: float
    end_hour: float  # may be < start_hour, meaning the session wraps past midnight

    def spans_midnight(self) -> bool:
        return self.end_hour <= self.start_hour


MARKET_SESSIONS: list[MarketSession] = [
    MarketSession("Sydney", 21.0, 6.0),
    MarketSession("Tokyo", 0.0, 9.0),
    MarketSession("London", 7.0, 16.0),
    MarketSession("New York", 12.0, 21.0),
]

# Cap the number of days we draw session bands for -- a multi-year dataset
# would otherwise produce thousands of shapes and stall the browser.
MAX_OVERLAY_DAYS = 14


class SessionOverlay:
    """Adds market session background bands and labels to a chart."""

    def __init__(self, sessions: list[MarketSession] | None = None) -> None:
        self.sessions = sessions or MARKET_SESSIONS

    def active_session(self, timestamp: pd.Timestamp) -> str | None:
        """Return the name of the session active at `timestamp` (UTC), or None."""
        hour = timestamp.hour + timestamp.minute / 60
        for session in self.sessions:
            if session.spans_midnight():
                if hour >= session.start_hour or hour < session.end_hour:
                    return session.name
            elif session.start_hour <= hour < session.end_hour:
                return session.name
        return None

    def add_to_figure(
        self,
        fig: go.Figure,
        df: pd.DataFrame,
        config=None,
        row: int | None = None,
        col: int | None = None,
        max_days: int = MAX_OVERLAY_DAYS,
    ) -> go.Figure:
        """Draw session background bands (and labels) over `df`'s date range.

        Only the most recent `max_days` days are drawn, to bound the
        number of shapes added to the figure.
        """
        theme = get_theme(config.theme) if config is not None else get_theme("dark")
        timestamps = df[DATETIME_COL].dropna()
        if timestamps.empty:
            return fig

        end_date = timestamps.max().normalize()
        start_date = max(timestamps.min().normalize(), end_date - pd.Timedelta(days=max_days - 1))
        active = self.active_session(timestamps.max())

        for day in pd.date_range(start_date, end_date, freq="1D"):
            label_day = day == end_date
            for session in self.sessions:
                self._add_session_band(fig, day, session, theme, active, row, col, label_day)
        return fig

    @staticmethod
    def _add_session_band(
        fig: go.Figure,
        day: pd.Timestamp,
        session: MarketSession,
        theme: ChartTheme,
        active_session: str | None,
        row: int | None,
        col: int | None,
        label: bool,
    ) -> None:
        start = day + pd.Timedelta(hours=session.start_hour)
        end_hour = session.end_hour + (24 if session.spans_midnight() else 0)
        end = day + pd.Timedelta(hours=end_hour)

        color = theme.session_colors.get(session.name, "rgba(128, 128, 128, 0.08)")
        is_active = session.name == active_session
        kwargs = dict(
            x0=start.isoformat(),
            x1=end.isoformat(),
            fillcolor=color,
            opacity=1.0 if is_active else 0.6,
            line_width=0,
            layer="below",
        )
        if label:
            kwargs.update(
                annotation_text=session.name,
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color=theme.text,
            )
        if row is not None and col is not None:
            fig.add_vrect(row=row, col=col, **kwargs)
        else:
            fig.add_vrect(**kwargs)
