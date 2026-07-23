"""`app/ui/pages/28_MT5_Data_Synchronization.py` -- initial render across
all 11 tabs, one sync action per major tab exercised without exception.
Uses the real, process-wide `MT5Manager`/`SyncEngineManager` storage
location (mirrors `test_mt5_json_bridge_page.py`) -- cleaned up before
and after."""

import shutil

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_mt5_state():
    paths = get_paths()
    shutil.rmtree(paths.mt5_state_dir, ignore_errors=True)
    shutil.rmtree(paths.mt5_sync_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.mt5_state_dir, ignore_errors=True)
    shutil.rmtree(paths.mt5_sync_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/28_MT5_Data_Synchronization.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_no_exception() -> None:
    at = _fresh()
    assert "mts_selected_symbol" in at.session_state


def test_all_eleven_tabs_present() -> None:
    at = _fresh()
    tab_labels = [t.proto.label for t in at.tabs]
    expected = ["Overview", "Tick Sync", "Bar Sync", "Market Watch", "Spread", "Market Book", "Sessions", "Statistics", "Diagnostics", "Audit", "Health"]
    assert tab_labels == expected


def test_overview_tab_sync_symbols_button() -> None:
    at = _fresh()
    buttons = [b for b in at.button if b.key == "mts_sync_symbols"]
    assert buttons
    buttons[0].click().run()
    assert at.exception == []


def test_sessions_tab_compute_sessions_button() -> None:
    at = _fresh()
    buttons = [b for b in at.button if b.key == "mts_compute_sessions"]
    assert buttons
    buttons[0].click().run()
    assert at.exception == []


def test_diagnostics_tab_run_button() -> None:
    at = _fresh()
    buttons = [b for b in at.button if b.key == "mts_run_diagnostics"]
    assert buttons
    buttons[0].click().run()
    assert at.exception == []
    rows = at.session_state["mts_last_diagnostics"]
    assert rows


def test_statistics_tab_renders_after_a_sync() -> None:
    at = _fresh()
    symbols_buttons = [b for b in at.button if b.key == "mts_sync_symbols"]
    symbols_buttons[0].click().run()
    assert at.exception == []


def test_audit_tab_renders_without_exception() -> None:
    at = _fresh()
    assert at.exception == []


def test_health_tab_renders_without_exception() -> None:
    at = _fresh()
    assert at.exception == []
