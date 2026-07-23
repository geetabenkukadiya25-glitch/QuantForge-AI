"""`app/ui/pages/23_Governance.py` -- initial render, create-record,
full approval lifecycle via toolbar buttons, delete two-step confirm,
and a real end-to-end compliance-report run via `AppTest`.

Uses the real, process-wide `GovernanceManager`/`DatasetManager` storage
locations (mirrors `test_risk_analytics_page.py`) -- cleaned up before
and after so this test stays repeatable."""

import shutil
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_governance_state():
    paths = get_paths()
    shutil.rmtree(paths.governance_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.governance_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/23_Governance.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def _create_record(at: AppTest, object_type: str = "DATASET", object_id: str = "d-fixture", label: str = "Fixture Dataset") -> AppTest:
    at.selectbox(key="gov_new_object_type").select(object_type).run()
    at.text_input(key="gov_new_object_id").set_value(object_id).run()
    at.text_input(key="gov_new_object_label").set_value(label).run()
    at.button(key="gov_create_record").click().run()
    assert at.exception == []
    return at


def test_initial_render_has_no_selection() -> None:
    at = _fresh()
    assert at.session_state["gov_selected_id"] is None


def test_create_record_selects_it() -> None:
    at = _fresh()
    at = _create_record(at)
    assert at.session_state["gov_selected_id"] is not None


def test_full_approval_lifecycle_via_toolbar() -> None:
    at = _fresh()
    at = _create_record(at)

    at.button(key="toolbar_submit").click().run()
    assert at.exception == []
    from app.governance import GovernanceStatus, get_governance_manager

    manager = get_governance_manager()
    record_id = at.session_state["gov_selected_id"]
    assert manager.get(record_id).status == GovernanceStatus.UNDER_REVIEW

    at.button(key="toolbar_approve").click().run()
    assert at.exception == []
    assert manager.get(record_id).status == GovernanceStatus.APPROVED

    at.button(key="toolbar_publish").click().run()
    assert at.exception == []
    assert manager.get(record_id).status == GovernanceStatus.PUBLISHED

    at.button(key="toolbar_toggle_lock").click().run()
    assert at.exception == []
    locked = manager.get(record_id)
    assert locked.status == GovernanceStatus.LOCKED
    assert locked.locked is True

    at.button(key="toolbar_toggle_lock").click().run()
    assert at.exception == []
    unlocked = manager.get(record_id)
    assert unlocked.status == GovernanceStatus.APPROVED
    assert unlocked.locked is False


def test_delete_requires_two_step_confirm() -> None:
    at = _fresh()
    at = _create_record(at)
    record_id = at.session_state["gov_selected_id"]

    at.button(key="toolbar_delete").click().run()
    assert at.exception == []
    assert at.session_state["gov_delete_armed"] is True

    cancel_btns = [b for b in at.button if b.label == "Cancel"]
    assert cancel_btns
    cancel_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["gov_delete_armed"] is False

    from app.governance import get_governance_manager

    assert get_governance_manager().get(record_id) is not None  # still exists -- cancel didn't delete

    at.button(key="toolbar_delete").click().run()
    confirm_btns = [b for b in at.button if b.label == "Confirm Delete"]
    assert confirm_btns
    confirm_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["gov_selected_id"] is None


def test_compliance_report_end_to_end() -> None:
    at = _fresh()
    at = _create_record(at)

    at.button(key="gov_run_compliance").click().run()
    assert at.exception == []

    from app.job_manager import JobState, get_job_manager

    job_manager = get_job_manager()
    deadline = time.time() + 15
    while "gov_last_compliance_report" not in at.session_state and time.time() < deadline:
        pending_job_id = at.session_state["gov_current_job_id"]
        if pending_job_id is not None and job_manager.get(pending_job_id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            time.sleep(0.02)
            continue
        at.run()
        assert at.exception == []

    assert "gov_last_compliance_report" in at.session_state
    report = at.session_state["gov_last_compliance_report"]
    assert report is not None
    assert report["sections"]["compliance"]["total_records"] == 1
