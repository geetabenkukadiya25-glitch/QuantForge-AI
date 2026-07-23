"""Shared fixtures for dataset_manager tests -- an isolated, temporary
registry/state directory pair per test, so nothing ever touches the real
`app/dataset_manager/registry` or `.../state` on disk."""

from pathlib import Path

import pytest

from app.dataset_manager.dataset_manager import DatasetManager

VALID_CSV = (
    b"Date,Time,Open,High,Low,Close,Volume,Spread\n"
    b"2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    b"2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
    b"2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2\n"
    b"2024.01.01,03:00,1.1010,1.1030,1.1000,1.1025,90,45\n"
)


@pytest.fixture
def dataset_dirs(tmp_path: Path) -> dict[str, Path]:
    return {"registry_dir": tmp_path / "registry", "state_dir": tmp_path / "state"}


@pytest.fixture
def manager(dataset_dirs: dict[str, Path]) -> DatasetManager:
    return DatasetManager(registry_dir=dataset_dirs["registry_dir"], state_dir=dataset_dirs["state_dir"])


@pytest.fixture
def valid_csv_bytes() -> bytes:
    return VALID_CSV
