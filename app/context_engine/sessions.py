"""Trading session window logic for the Market Context Engine.

Intentionally a separate, self-contained implementation from
`app.chart_engine.sessions` (which owns Plotly-rendering concerns
alongside its session table). Business/domain code (this module) must
not depend on a presentation-layer module, so the small, stable set of
session UTC windows is kept here independently -- the same
architectural trade-off already used between `data_engine` and
`chart_engine` for timeframe resampling.

Session hours are approximate, fixed UTC windows (DST is not modeled) --
sufficient for descriptive market context, not for precision
session-boundary trading logic.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class SessionWindow:
    """A trading session's approximate UTC open/close hour (0-24, may wrap midnight)."""

    name: str
    start_hour: float
    end_hour: float  # may be <= start_hour, meaning the session wraps past midnight

    def spans_midnight(self) -> bool:
        return self.end_hour <= self.start_hour


SESSION_WINDOWS: list[SessionWindow] = [
    SessionWindow("Sydney", 21.0, 6.0),
    SessionWindow("Tokyo", 0.0, 9.0),
    SessionWindow("London", 7.0, 16.0),
    SessionWindow("New York", 12.0, 21.0),
]


@dataclass(frozen=True)
class ActiveSessionInfo:
    """The trading session active at a given instant, and how far through it."""

    name: str | None
    progress_pct: float | None
    session_open: datetime | None
    session_close: datetime | None


def get_active_session(moment: datetime, windows: list[SessionWindow] | None = None) -> ActiveSessionInfo:
    """Return the first matching session window active at `moment` (assumed UTC).

    If multiple sessions overlap, the first match in `windows` order wins
    (matching real-world forex session overlaps, e.g. Tokyo/London).
    """
    windows = windows or SESSION_WINDOWS
    hour = moment.hour + moment.minute / 60 + moment.second / 3600

    for window in windows:
        if window.spans_midnight():
            active = hour >= window.start_hour or hour < window.end_hour
        else:
            active = window.start_hour <= hour < window.end_hour
        if not active:
            continue

        session_open, session_close = _session_bounds(moment, window)
        total_seconds = (session_close - session_open).total_seconds()
        elapsed_seconds = (moment - session_open).total_seconds()
        progress_pct = (elapsed_seconds / total_seconds * 100) if total_seconds > 0 else 0.0
        return ActiveSessionInfo(window.name, round(progress_pct, 2), session_open, session_close)

    return ActiveSessionInfo(None, None, None, None)


def _session_bounds(moment: datetime, window: SessionWindow) -> tuple[datetime, datetime]:
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if window.spans_midnight() and moment.hour < window.end_hour:
        # We're past midnight, inside a session that opened "yesterday".
        session_open = day - timedelta(days=1) + timedelta(hours=window.start_hour)
        session_close = day + timedelta(hours=window.end_hour)
    else:
        session_open = day + timedelta(hours=window.start_hour)
        end_hour = window.end_hour + (24 if window.spans_midnight() else 0)
        session_close = day + timedelta(hours=end_hour)
    return session_open, session_close


def is_weekend(moment: datetime) -> bool:
    """True on Saturday, and Sunday before the market re-opens (~21:00 UTC)."""
    weekday = moment.weekday()  # Monday=0 ... Sunday=6
    if weekday == 5:  # Saturday
        return True
    if weekday == 6:  # Sunday
        return moment.hour < 21
    if weekday == 4:  # Friday
        return moment.hour >= 21
    return False


def is_market_open(moment: datetime) -> bool:
    """Approximate forex-style ~24/5 market open check (see `is_weekend`)."""
    return not is_weekend(moment)


def to_utc(moment: datetime) -> datetime:
    """Return `moment` as an aware UTC datetime, assuming naive input is already UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
