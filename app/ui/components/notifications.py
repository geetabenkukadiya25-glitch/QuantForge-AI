"""Central notification wrapper -- routes what pages already show via
`st.success`/`st.info`/`st.warning`/`st.error` through one function so a
Notification Center can list history, without changing any visible
message text. Pure presentation; introduces one additive, `qf_`-prefixed
session-state key (`qf_notifications`).
"""

from datetime import datetime
from typing import Literal

import streamlit as st

_KIND_FN = {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}
_KIND_ICON = {"success": "✅", "info": "ℹ️", "warning": "⚠️", "error": "❌"}
_MAX_HISTORY = 50

NotificationKind = Literal["success", "info", "warning", "error"]


def notify(kind: NotificationKind, message: str) -> None:
    """Show `message` exactly as `st.<kind>(message)` already would, and
    log it into `qf_notifications` (capped at the most recent 50) for
    `render_notification_center()`."""
    _KIND_FN[kind](message)
    history = st.session_state.setdefault("qf_notifications", [])
    history.insert(0, {"kind": kind, "message": message, "ts": datetime.now()})
    del history[_MAX_HISTORY:]


def render_notification_center() -> None:
    history = st.session_state.get("qf_notifications", [])
    with st.popover(f"🔔 Notifications ({len(history)})"):
        if not history:
            st.caption("No notifications yet.")
        for entry in history:
            st.caption(f"{_KIND_ICON[entry['kind']]} {entry['ts'].strftime('%H:%M:%S')} — {entry['message']}")
