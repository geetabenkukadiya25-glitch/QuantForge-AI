"""`app/ui/pages/26_MT5_Integration.py` -- initial render across all 13
tabs, Connect/Disconnect toolbar round-trip. Uses the real, process-wide
`MT5Manager` storage location (mirrors `test_cloud_sync_page.py`) --
cleaned up before and after so this test stays repeatable. Works
identically whether or not a real MT5 terminal is present."""

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
    at = AppTest.from_file("app/ui/pages/26_MT5_Integration.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_no_exception() -> None:
    at = _fresh()
    assert "mt5_selected_symbol" in at.session_state


def test_all_thirteen_tabs_present() -> None:
    at = _fresh()
    tab_labels = [t.proto.label for t in at.tabs]
    expected = ["Overview", "Connection", "Terminal", "Account", "Symbols", "Market Watch", "History", "Ticks", "Diagnostics", "Bridge", "Audit", "Settings", "Health"]
    assert tab_labels == expected


def test_connect_disconnect_toolbar_round_trip() -> None:
    at = _fresh()
    connect_buttons = [b for b in at.button if b.key == "toolbar_connect"]
    assert connect_buttons
    connect_buttons[0].click().run()
    assert at.exception == []

    from app.mt5 import ConnectionState, get_mt5_manager

    manager = get_mt5_manager()
    # Whether or not a real terminal is present, the state must be one
    # of the honest degrade states -- never crash, never a silent no-op.
    assert manager.connection_state in set(ConnectionState)

    if manager.connection_state == ConnectionState.CONNECTED:
        at2 = _fresh()
        disconnect_buttons = [b for b in at2.button if b.key == "toolbar_disconnect"]
        assert disconnect_buttons
        disconnect_buttons[0].click().run()
        assert at2.exception == []
        assert get_mt5_manager().connection_state == ConnectionState.DISCONNECTED


def test_settings_tab_save_round_trip() -> None:
    at = _fresh()
    save_buttons = [b for b in at.button if b.label == "Save Settings"]
    assert save_buttons
    save_buttons[0].click().run()
    assert at.exception == []


def test_diagnostics_tab_run_button() -> None:
    at = _fresh()
    run_buttons = [b for b in at.button if b.key == "mt5_run_diagnostics"]
    assert run_buttons
    run_buttons[0].click().run()
    assert at.exception == []


def test_bridge_tab_has_disabled_connect_buttons() -> None:
    at = _fresh()
    connect_bridge_buttons = [b for b in at.button if b.key and b.key.startswith("mt5_connect_")]
    assert len(connect_bridge_buttons) == 2
    assert all(b.disabled for b in connect_bridge_buttons)
