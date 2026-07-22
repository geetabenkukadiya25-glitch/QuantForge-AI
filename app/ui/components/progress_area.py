"""Documents the new `ProgressTracker` call-site convention for Phase
18.2/18.3: render into a placeholder living in the Workspace toolbar area
or Information column instead of `st.sidebar.empty()`. `ProgressTracker`
itself (`app.ui.progress`) is untouched by this module -- these are thin
placeholder helpers only.
"""

import streamlit as st

from app.ui.progress import ProgressTracker


def new_progress_placeholder(container=None):
    target = container if container is not None else st
    return target.empty()


def render_progress(tracker: ProgressTracker, placeholder) -> None:
    with placeholder.container():
        tracker.render()
