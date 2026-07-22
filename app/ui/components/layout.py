"""Shared page-shell and toolbar components.

Extracted from the 3-column IDE layout (`st.columns([1, 3, 1])`) and the
toolbar-of-buttons row (`st.columns(N)`) already used and verified in
`app/ui/pages/3_Strategy_Library.py`, so every dashboard can share the
exact same skeleton instead of re-implementing it per page. Pure
presentation -- no engine, SDL, or business-logic imports.
"""

from dataclasses import dataclass

import streamlit as st


def render_shell(gap: str = "medium"):
    """3-column Explorer / Workspace / Information shell, the same fixed
    20/60/20 (`[1, 3, 1]`) ratio already used by Strategy Library.
    Streamlit has no drag-resizable columns -- this is a fixed-ratio
    approximation, same honest limitation already documented there."""
    return st.columns([1, 3, 1], gap=gap)


@dataclass
class ToolbarAction:
    """One toolbar button. `enabled=False` renders a disabled button with
    `disabled_reason` as its tooltip -- used for any action a page has no
    existing wired implementation for (e.g. "Stop", when an engine has no
    cancellation support), so nothing is ever fabricated."""

    label: str
    key: str
    enabled: bool = True
    disabled_reason: str | None = None
    type: str = "secondary"


def render_toolbar(actions: list[ToolbarAction], container=None) -> dict[str, bool]:
    """Render one row of toolbar buttons (the `st.columns(len(actions))`-
    of-buttons idiom already used by Strategy Library's center toolbar)
    and return `{action.key: clicked}` for the caller's existing button-
    handling logic to branch on, unchanged."""
    target = container if container is not None else st
    if not actions:
        return {}
    cols = target.columns(len(actions))
    clicked: dict[str, bool] = {}
    for col, action in zip(cols, actions):
        clicked[action.key] = col.button(
            action.label,
            key=f"toolbar_{action.key}",
            disabled=not action.enabled,
            help=action.disabled_reason if not action.enabled else None,
            type=action.type,
            use_container_width=True,
        )
    return clicked
