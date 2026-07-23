"""Shared fixtures for `app.settings_center` tests -- an isolated,
temporary state directory per test, mirrors `tests/governance/conftest.py`."""

from pathlib import Path

import pytest

from app.settings_center.settings_manager import SettingsCenterManager


@pytest.fixture
def settings_manager(tmp_path: Path) -> SettingsCenterManager:
    return SettingsCenterManager(state_dir=tmp_path / "settings_state")
