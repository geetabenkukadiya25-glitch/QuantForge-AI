"""`app/ui/pages/27_MT5_JSON_Bridge.py` -- initial render across all 10
tabs, Export tab produces a payload, Validation tab flags a
deliberately-malformed pasted document, Import tab applies a
`HEALTH_REQUEST`. Uses the real, process-wide `MT5Manager`/
`BridgeExchangeManager` storage location (mirrors
`test_mt5_integration_page.py`) -- cleaned up before and after."""

import shutil

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_mt5_state():
    paths = get_paths()
    shutil.rmtree(paths.mt5_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.mt5_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/27_MT5_JSON_Bridge.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_no_exception() -> None:
    at = _fresh()
    assert "mtb_last_export" in at.session_state


def test_all_ten_tabs_present() -> None:
    at = _fresh()
    tab_labels = [t.proto.label for t in at.tabs]
    expected = ["Overview", "Export", "Import", "Schema", "Payload", "Validation", "Health", "Audit", "Statistics", "Explorer"]
    assert tab_labels == expected


def test_export_tab_generates_a_payload() -> None:
    at = _fresh()
    submit_buttons = [b for b in at.button if b.label == "Generate Export"]
    assert submit_buttons
    submit_buttons[0].click().run()
    assert at.exception == []
    assert at.session_state["mtb_last_export"] is not None
    assert "checksum" in at.session_state["mtb_last_export"]


def test_validation_tab_flags_malformed_document() -> None:
    at = _fresh()
    text_areas = [t for t in at.text_area if t.key == "mtb_validate_raw"]
    assert text_areas
    text_areas[0].set_value("{not valid json").run()
    validate_buttons = [b for b in at.button if b.key == "mtb_run_validate"]
    assert validate_buttons
    validate_buttons[0].click().run()
    assert at.exception == []
    issues = at.session_state["mtb_validation_issues"]
    assert issues
    assert any("Malformed JSON" in i for i in issues)


def test_import_tab_applies_health_request() -> None:
    at = _fresh()
    text_areas = [t for t in at.text_area if t.key == "mtb_import_raw"]
    assert text_areas
    text_areas[0].set_value('{"kind": "HEALTH_REQUEST", "params": {}}').run()
    apply_buttons = [b for b in at.button if b.key == "mtb_apply_import"]
    assert apply_buttons
    apply_buttons[0].click().run()
    assert at.exception == []
    result = at.session_state["mtb_last_import_result"]
    assert result["success"] is True


def test_import_tab_rejects_forbidden_keyword() -> None:
    at = _fresh()
    text_areas = [t for t in at.text_area if t.key == "mtb_import_raw"]
    text_areas[0].set_value('{"kind": "SELECT_SYMBOL", "params": {"symbol": "EURUSD"}, "buy": true}').run()
    apply_buttons = [b for b in at.button if b.key == "mtb_apply_import"]
    apply_buttons[0].click().run()
    assert at.exception == []
    result = at.session_state["mtb_last_import_result"]
    assert result["success"] is False
    assert any("forbidden keyword" in i for i in result["issues"])


def test_explorer_tab_has_two_disabled_connect_buttons() -> None:
    at = _fresh()
    connect_buttons = [b for b in at.button if b.key and b.key.startswith("mtb_connect_")]
    assert len(connect_buttons) == 2
    assert all(b.disabled for b in connect_buttons)
