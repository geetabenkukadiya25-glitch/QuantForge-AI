"""Tests for CSVImporter."""

import pytest

from app.data_engine.columns import STANDARD_COLUMNS
from app.data_engine.csv_importer import CSVImporter
from app.data_engine.exceptions import CSVFormatError


def test_import_valid_csv_produces_standard_schema(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    assert list(df.columns) == STANDARD_COLUMNS
    assert len(df) == 5


def test_import_merges_date_and_time(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    assert df["Datetime"].iloc[0].isoformat() == "2024-01-01T00:00:00"


def test_import_mt5_export_format(mt5_export_csv_path) -> None:
    df = CSVImporter().import_csv(mt5_export_csv_path)
    assert list(df.columns) == STANDARD_COLUMNS
    assert len(df) == 3
    assert df["Volume"].iloc[0] == 50


def test_import_missing_ohlc_column_raises(corrupted_csv_path) -> None:
    with pytest.raises(CSVFormatError):
        CSVImporter().import_csv(corrupted_csv_path)


def test_import_missing_file_raises(tmp_path) -> None:
    with pytest.raises(CSVFormatError):
        CSVImporter().import_csv(tmp_path / "does_not_exist.csv")


def test_import_empty_file_raises(tmp_path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(CSVFormatError):
        CSVImporter().import_csv(empty)
