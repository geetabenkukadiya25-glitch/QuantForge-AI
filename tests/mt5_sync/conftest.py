"""Shared fixtures for `app.mt5_sync` tests -- an isolated, temporary
state directory per test, mirrors `tests/mt5/conftest.py` and
`tests/cloud_sync/conftest.py`. Reuses `tests.mt5.conftest`'s
`requires_real_terminal` marker rather than duplicating the real-
terminal probe."""

from pathlib import Path

import pytest

from app.mt5.terminal_manager import MT5Manager
from app.mt5_sync.sync_manager import SyncEngineManager
from tests.mt5.conftest import has_real_terminal, requires_real_terminal  # noqa: F401 -- re-exported fixture + marker

__all__ = ["has_real_terminal", "requires_real_terminal"]


@pytest.fixture
def mt5_manager(tmp_path: Path) -> MT5Manager:
    return MT5Manager(state_dir=tmp_path / "mt5_state")


@pytest.fixture
def sync_manager(mt5_manager: MT5Manager, tmp_path: Path) -> SyncEngineManager:
    return SyncEngineManager(state_dir=tmp_path / "mt5_sync_state", mt5_manager=mt5_manager)
