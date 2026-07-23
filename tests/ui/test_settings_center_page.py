"""`app/ui/pages/24_Settings_Center.py` -- initial render, save a
section, reset-all two-step confirm, path override change/reset, and a
real end-to-end Export via `AppTest`.

Uses the real, process-wide `SettingsCenterManager` storage location
(mirrors `test_governance_page.py`) -- cleaned up before and after so
this test stays repeatable. Deliberately never clicks "Open Folder" --
that spawns a real OS file-browser process, which has no place in an
automated test."""

import shutil
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_settings_state():
    paths = get_paths()
    shutil.rmtree(paths.settings_center_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.settings_center_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/24_Settings_Center.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_no_exception() -> None:
    at = _fresh()
    assert at.session_state["set_current_job_id"] is None


def test_save_general_section_via_form() -> None:
    at = _fresh()
    project_name_input = [w for w in at.text_input if w.label == "Project Name"][0]
    project_name_input.set_value("My Custom Project").run()
    save_btns = [b for b in at.button if b.label == "Save"]
    assert save_btns
    save_btns[0].click().run()
    assert at.exception == []

    from app.settings_center import get_settings_center_manager

    assert get_settings_center_manager().get_state().general.project_name == "My Custom Project"


def test_reset_all_requires_two_step_confirm() -> None:
    at = _fresh()
    from app.settings_center import get_settings_center_manager

    manager = get_settings_center_manager()
    manager.update_section("general", project_name="Should Survive Cancel")

    at.button(key="set_quick_reset_all").click().run()
    assert at.exception == []
    assert at.session_state["set_reset_all_armed"] is True

    cancel_btns = [b for b in at.button if b.key == "set_cancel_reset_all"]
    assert cancel_btns
    cancel_btns[0].click().run()
    assert at.exception == []
    assert manager.get_state().general.project_name == "Should Survive Cancel"

    at.button(key="set_quick_reset_all").click().run()
    confirm_btns = [b for b in at.button if b.key == "set_confirm_reset_all"]
    assert confirm_btns
    confirm_btns[0].click().run()
    assert at.exception == []
    assert manager.get_state().general.project_name != "Should Survive Cancel"


def test_path_override_change_and_reset() -> None:
    at = _fresh()
    from app.settings_center import get_settings_center_manager

    manager = get_settings_center_manager()

    change_inputs = [w for w in at.text_input if w.key and w.key.startswith("set_change_input_")]
    assert change_inputs
    target_key = change_inputs[0].key.replace("set_change_input_", "")
    change_inputs[0].set_value("/my/override/path").run()

    change_btn = at.button(key=f"set_change_{target_key}")
    change_btn.click().run()
    assert at.exception == []
    assert manager.get_state().path_overrides.get(target_key) == "/my/override/path"

    reset_btn = at.button(key=f"set_reset_{target_key}")
    reset_btn.click().run()
    assert at.exception == []
    assert target_key not in manager.get_state().path_overrides


def test_export_settings_end_to_end() -> None:
    at = _fresh()
    at.button(key="set_quick_export").click().run()
    assert at.exception == []

    from app.job_manager import JobState, get_job_manager

    job_manager = get_job_manager()
    deadline = time.time() + 15
    while at.session_state["set_last_export"] is None and time.time() < deadline:
        pending_job_id = at.session_state["set_current_job_id"]
        if pending_job_id is not None and job_manager.get(pending_job_id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            time.sleep(0.02)
            continue
        at.run()
        assert at.exception == []

    assert at.session_state["set_last_export"] is not None
    assert b"general" in at.session_state["set_last_export"]
