"""Shared bordered-card components.

Extracted from the repeated `st.container(border=True)` + bold title +
`st.write` rows idiom already used six times in Strategy Library's
Information panel, and the bordered-card-per-entry idiom used by its
`_render_strategy_card` helper. Pure presentation.
"""

from typing import Callable, Iterable

import streamlit as st


def render_info_card(title: str, rows: Iterable[tuple[str, str]], container=None) -> None:
    """One bordered card: a bold title line, then one `label: value` line
    per row -- matches Strategy Library's Information panel cards
    (General Information / Market / Statistics / Flags) exactly."""
    target = container if container is not None else st
    with target.container(border=True):
        st.markdown(f"**{title}**")
        for label, value in rows:
            st.write(f"{label}: {value}")


def render_list_card(
    title: str,
    items: list,
    render_item: Callable[[object], None],
    container=None,
    empty_caption: str = "Nothing to show yet.",
) -> None:
    """A titled list of bordered item-cards -- generalizes Strategy
    Library's `_render_strategy_card` (one bordered card per Explorer
    entry) for any Explorer-column list (datasets, recent runs,
    strategies). `render_item(item)` renders one item's card body; this
    only supplies the title and the empty-state caption."""
    target = container if container is not None else st
    if title:
        target.markdown(f"**{title}**")
    if not items:
        target.caption(empty_caption)
        return
    for item in items:
        render_item(item)
