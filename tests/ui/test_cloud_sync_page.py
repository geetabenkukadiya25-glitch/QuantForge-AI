"""`app/ui/pages/25_Cloud_Sync.py` -- initial render, queue-a-settings-
sync + full toolbar lifecycle, artifact registration, snapshot creation,
and policy save via `AppTest`.

Uses the real, process-wide `SyncManager` storage location (mirrors
`test_governance_page.py`) -- cleaned up before and after so this test
stays repeatable."""

import shutil

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_cloud_sync_state():
    paths = get_paths()
    shutil.rmtree(paths.cloud_sync_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.cloud_sync_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/25_Cloud_Sync.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_no_exception() -> None:
    at = _fresh()
    assert at.session_state["syn_selected_operation_id"] is None


def test_queue_settings_sync_and_full_toolbar_lifecycle() -> None:
    at = _fresh()
    at.selectbox(key="syn_new_kind").select("SETTINGS").run()
    at.button(key="syn_queue_settings").click().run()
    assert at.exception == []
    operation_id = at.session_state["syn_selected_operation_id"]
    assert operation_id is not None

    from app.cloud_sync import SyncOperationStatus, get_sync_manager

    manager = get_sync_manager()
    assert manager.get_operation(operation_id).status == SyncOperationStatus.QUEUED

    at.button(key="toolbar_mark_running").click().run()
    assert at.exception == []
    assert manager.get_operation(operation_id).status == SyncOperationStatus.RUNNING

    at.button(key="toolbar_mark_completed").click().run()
    assert at.exception == []
    assert manager.get_operation(operation_id).status == SyncOperationStatus.COMPLETED


def test_register_artifact_via_form() -> None:
    at = _fresh()
    object_id_input = [w for w in at.text_input if w.key == "syn_artifact_object_id"][0]
    object_id_input.set_value("some-object-id").run()
    submit_btns = [b for b in at.button if b.label == "Register Artifact"]
    assert submit_btns
    submit_btns[0].click().run()
    assert at.exception == []

    from app.cloud_sync import get_sync_manager

    artifacts = get_sync_manager().list_artifacts()
    assert any(a.object_id == "some-object-id" for a in artifacts)


def test_create_snapshot_via_form() -> None:
    at = _fresh()
    label_input = [w for w in at.text_input if w.key == "syn_snapshot_label"][0]
    label_input.set_value("My Snapshot").run()
    submit_btns = [b for b in at.button if b.label == "Create Snapshot"]
    assert submit_btns
    submit_btns[0].click().run()
    assert at.exception == []

    from app.cloud_sync import get_sync_manager

    snapshots = get_sync_manager().list_snapshots()
    assert any(s.label == "My Snapshot" for s in snapshots)


def test_save_policy_via_form() -> None:
    at = _fresh()
    save_btns = [b for b in at.button if b.label == "Save Policy"]
    assert save_btns
    save_btns[0].click().run()
    assert at.exception == []


def test_providers_tab_has_six_disabled_connect_buttons() -> None:
    at = _fresh()
    connect_btns = [b for b in at.button if b.key and b.key.startswith("syn_connect_")]
    assert len(connect_btns) == 6
    assert all(b.disabled for b in connect_btns)
