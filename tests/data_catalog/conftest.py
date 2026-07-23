"""Shared fixtures for data_catalog tests -- an isolated, temporary
dataset registry/state dir, catalog state dir, and job history dir per
test, so nothing ever touches real on-disk state."""

from pathlib import Path

import pytest

from app.data_catalog.catalog import DataCatalog
from app.dataset_manager.dataset_manager import DatasetManager
from app.job_manager.job_manager import JobManager

VALID_CSV = (
    b"Date,Time,Open,High,Low,Close,Volume,Spread\n"
    b"2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    b"2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
    b"2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2\n"
    b"2024.01.01,03:00,1.1010,1.1030,1.1000,1.1025,90,45\n"
)


@pytest.fixture
def dataset_manager(tmp_path: Path) -> DatasetManager:
    return DatasetManager(registry_dir=tmp_path / "registry", state_dir=tmp_path / "dm_state")


@pytest.fixture
def job_history_dir(tmp_path: Path) -> Path:
    return tmp_path / "jobs_history"


@pytest.fixture
def job_manager(job_history_dir: Path) -> JobManager:
    return JobManager(history_dir=job_history_dir)


@pytest.fixture
def catalog(tmp_path: Path, dataset_manager: DatasetManager, job_manager: JobManager) -> DataCatalog:
    return DataCatalog(state_dir=tmp_path / "catalog_state", dataset_manager=dataset_manager, job_manager=job_manager)


@pytest.fixture
def valid_csv_bytes() -> bytes:
    return VALID_CSV
