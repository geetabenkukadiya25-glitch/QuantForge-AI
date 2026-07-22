"""Shared, presentation-only UI components for the institutional workspace
standard (Phase 18.2/18.3): a 3-column page shell, a toolbar-of-actions
row, bordered info/list cards, a bottom status bar, a notification center,
and a command bar.

Every component here is extracted from patterns already used and verified
in `app/ui/pages/3_Strategy_Library.py` (Phase 18.1), or is new but strictly
navigation/read-only. None of these modules import any engine, SDL, or
business-logic module -- they only read state a page already computes
(session-state keys, `app.ui.state`, `app.ui.progress`) and render it.
"""

from app.ui.components.cards import render_info_card, render_list_card
from app.ui.components.command_bar import render_command_bar
from app.ui.components.job_panel import render_job_panel
from app.ui.components.layout import ToolbarAction, render_shell, render_toolbar
from app.ui.components.notifications import notify, render_notification_center
from app.ui.components.progress_area import new_progress_placeholder, render_progress
from app.ui.components.runtime_monitor import render_runtime_monitor
from app.ui.components.status_bar import render_status_bar

__all__ = [
    "render_info_card",
    "render_list_card",
    "render_command_bar",
    "render_job_panel",
    "ToolbarAction",
    "render_shell",
    "render_toolbar",
    "notify",
    "render_notification_center",
    "new_progress_placeholder",
    "render_progress",
    "render_runtime_monitor",
    "render_status_bar",
]
