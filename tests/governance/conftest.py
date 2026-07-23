"""Shared fixtures for `app.governance` tests -- an isolated, temporary
state directory per test, mirrors `tests/risk_analytics/conftest.py` and
`tests/workflow/conftest.py`."""

from pathlib import Path

import pytest

from app.governance.governance_manager import GovernanceManager


@pytest.fixture
def governance_manager(tmp_path: Path) -> GovernanceManager:
    return GovernanceManager(state_dir=tmp_path / "governance_state")
