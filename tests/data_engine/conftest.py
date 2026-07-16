"""Shared fixtures for data_engine tests."""

from pathlib import Path

import pytest

VALID_CSV = """Date,Time,Open,High,Low,Close,Tick Volume,Volume,Spread
2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,100,50,2
2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,120,60,2
2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,110,55,2
2024.01.01,03:00,1.1010,1.1030,1.1000,1.1025,90,45,2
2024.01.01,04:00,1.1025,1.1040,1.1015,1.1035,130,65,2
"""

MT5_EXPORT_CSV = (
    "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
    "2024.01.01\t00:00:00\t1.1000\t1.1010\t1.0990\t1.1005\t100\t50\t2\n"
    "2024.01.01\t01:00:00\t1.1005\t1.1020\t1.1000\t1.1015\t120\t60\t2\n"
    "2024.01.01\t02:00:00\t1.1015\t1.1025\t1.1005\t1.1010\t110\t55\t2\n"
)

CORRUPTED_CSV = """Date,Time,Open,High,Close,Spread
2024.01.01,00:00,1.1000,1.1010,1.1005,2
2024.01.01,01:00,1.1005,1.1020,1.1015,2
"""

DUPLICATE_CSV = """Date,Time,Open,High,Low,Close,Volume,Spread
2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2
2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2
2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2
"""

MISSING_VALUES_CSV = """Date,Time,Open,High,Low,Close,Volume,Spread
2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2
2024.01.01,01:00,,1.1020,1.1000,1.1015,60,2
2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2
"""

INVALID_OHLC_CSV = """Date,Time,Open,High,Low,Close,Volume,Spread
2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2
2024.01.01,01:00,1.2000,1.1020,1.1000,1.1015,60,2
2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def valid_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "valid.csv", VALID_CSV)


@pytest.fixture
def mt5_export_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "mt5_export.csv", MT5_EXPORT_CSV)


@pytest.fixture
def corrupted_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "corrupted.csv", CORRUPTED_CSV)


@pytest.fixture
def duplicate_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "duplicate.csv", DUPLICATE_CSV)


@pytest.fixture
def missing_values_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "missing_values.csv", MISSING_VALUES_CSV)


@pytest.fixture
def invalid_ohlc_csv_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "invalid_ohlc.csv", INVALID_OHLC_CSV)
