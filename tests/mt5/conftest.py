"""Shared fixtures for `app.mt5` tests -- an isolated, temporary state
directory per test, mirrors `tests/cloud_sync/conftest.py`. Also
provides a `has_real_terminal` flag so tests can skip terminal-dependent
assertions cleanly rather than fail on machines with no MT5 installed --
"never fabricate connection" applies to the test suite too.
"""

from pathlib import Path

import pytest

from app.mt5.connection_manager import import_mt5
from app.mt5.exceptions import MT5NotInstalledError
from app.mt5.mt5_models import ConnectionState
from app.mt5.terminal_manager import MT5Manager


@pytest.fixture
def mt5_manager(tmp_path: Path) -> MT5Manager:
    return MT5Manager(state_dir=tmp_path / "mt5_state")


def _real_terminal_connected() -> bool:
    try:
        mt5 = import_mt5()
    except MT5NotInstalledError:
        return False
    try:
        connected = bool(mt5.initialize())
        if connected:
            mt5.shutdown()
        return connected
    except Exception:  # noqa: BLE001 -- best-effort probe only, never fails the test collection
        return False


@pytest.fixture(scope="session")
def has_real_terminal() -> bool:
    return _real_terminal_connected()


requires_real_terminal = pytest.mark.skipif(
    not _real_terminal_connected(),
    reason="No real MT5 terminal available in this environment.",
)
