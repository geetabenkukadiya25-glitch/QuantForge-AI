"""Shared fixtures for `app.cloud_sync` tests -- an isolated, temporary
state directory per test, mirrors `tests/governance/conftest.py`."""

from pathlib import Path

import pytest

from app.cloud_sync.sync_manager import SyncManager


@pytest.fixture
def sync_manager(tmp_path: Path) -> SyncManager:
    return SyncManager(state_dir=tmp_path / "cloud_sync_state")
