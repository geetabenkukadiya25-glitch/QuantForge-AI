"""Shared fixtures for job_manager tests -- every test gets a fresh
`JobManager` backed by an isolated `tmp_path` history directory, so
nothing ever touches the real `app/runtime/jobs/` on disk and no
dispatcher thread/state leaks between tests."""

from pathlib import Path

import pytest

from app.job_manager.job_manager import JobManager


@pytest.fixture
def job_manager(tmp_path: Path) -> JobManager:
    return JobManager(history_dir=tmp_path / "jobs")
