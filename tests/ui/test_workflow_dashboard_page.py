"""`app/ui/pages/21_Workflow_Dashboard.py` -- create, template
instantiation, favorite, archive/restore, and a real end-to-end run
(CUSTOM_PLACEHOLDER step, no external dependencies) via `AppTest`.

Uses the real, process-wide `WorkflowManager` storage location (the page
constructs `WorkflowManager()` directly, same as `DatasetManager()`
elsewhere) -- cleaned up before and after so this test stays repeatable."""

import shutil
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_workflow_state():
    paths = get_paths()
    shutil.rmtree(paths.workflow_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.workflow_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/21_Workflow_Dashboard.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_has_no_selection() -> None:
    at = _fresh()
    assert at.session_state["wf_selected_id"] is None


def test_create_from_template_selects_it() -> None:
    at = _fresh()
    template_btns = [b for b in at.button if b.label == "Use Template"]
    assert template_btns
    template_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["wf_selected_id"] is not None


def test_new_workflow_favorite_archive_restore() -> None:
    at = _fresh()
    at.button(key="wf_new").click().run()
    assert at.exception == []
    assert at.session_state["wf_selected_id"] is not None

    fav_btns = [b for b in at.button if "Favorite" in b.label or "Unfavorite" in b.label]
    fav_btns[0].click().run()
    assert at.exception == []

    archive_btns = [b for b in at.button if "Archive" in b.label]
    archive_btns[0].click().run()
    assert at.exception == []

    restore_btns = [b for b in at.button if "Restore" in b.label]
    restore_btns[0].click().run()
    assert at.exception == []


def test_new_workflow_run_to_completion_end_to_end() -> None:
    """Build a workflow with a single CUSTOM_PLACEHOLDER step (no dataset/
    strategy dependency needed) entirely through the page's own widgets,
    Run it, and confirm the run genuinely reaches a terminal state via
    the real `WorkflowManager`/`JobManager` -- never fabricated."""
    at = _fresh()
    at.button(key="wf_new").click().run()
    workflow_id = at.session_state["wf_selected_id"]

    at.selectbox(key="wf_new_step_type").select("CUSTOM_PLACEHOLDER").run()
    at.text_input(key="wf_new_step_name").set_value("Solo Step").run()
    at.button(key="wf_add_step").click().run()
    assert at.exception == []

    run_btns = [b for b in at.button if b.label == "▶ Run"]
    assert run_btns
    run_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["wf_current_run_id"] is not None

    from app.workflow import WorkflowStatus, get_workflow_manager

    manager = get_workflow_manager()
    run_id = at.session_state["wf_current_run_id"]
    deadline = time.time() + 15
    while time.time() < deadline:
        run = manager.get_run(run_id)
        if run.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            break
        time.sleep(0.05)
    assert manager.get_run(run_id).status == WorkflowStatus.COMPLETED
    assert manager.get(workflow_id).status == WorkflowStatus.COMPLETED
