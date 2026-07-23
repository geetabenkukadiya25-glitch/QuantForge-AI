"""Session synchronization (Phase 19.2) -- pure computation of the 4
standard FX trading session windows against UTC time. No MT5 call: the
UTC ranges below are the conventional, broker-independent session
hours; if a future phase wants broker-specific session data, that
would come from `terminal_info()`'s server-time offset, layered on top
of this without changing these fixed windows.
"""

from datetime import datetime, time, timezone

from app.mt5_sync.sync_models import SessionWindow

_SESSIONS: tuple[tuple[str, time, time], ...] = (
    ("Sydney", time(22, 0), time(7, 0)),  # wraps midnight UTC
    ("Tokyo", time(0, 0), time(9, 0)),
    ("London", time(8, 0), time(17, 0)),
    ("New York", time(13, 0), time(22, 0)),
)


def _is_active(now: time, open_: time, close: time) -> bool:
    if open_ <= close:
        return open_ <= now < close
    return now >= open_ or now < close  # wraps past midnight


def compute_sessions(now_utc: datetime | None = None) -> list[SessionWindow]:
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    current_time = now_utc.timetz().replace(tzinfo=None) if now_utc.tzinfo else now_utc.time()
    return [
        SessionWindow(name=name, utc_open=open_, utc_close=close, is_active=_is_active(current_time, open_, close))
        for name, open_, close in _SESSIONS
    ]
