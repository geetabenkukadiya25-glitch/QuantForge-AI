"""Tests for DataCleaner."""

from app.data_engine.cleaner import DataCleaner
from app.data_engine.csv_importer import CSVImporter
from app.data_engine.validator import DataValidator


def test_clean_removes_duplicate_candles(duplicate_csv_path) -> None:
    df = CSVImporter().import_csv(duplicate_csv_path)
    cleaned = DataCleaner().clean(df)
    assert len(cleaned) == 2
    assert cleaned["Datetime"].is_unique


def test_clean_sorts_by_datetime(duplicate_csv_path) -> None:
    df = CSVImporter().import_csv(duplicate_csv_path).iloc[::-1].reset_index(drop=True)
    cleaned = DataCleaner().clean(df)
    assert cleaned["Datetime"].is_monotonic_increasing


def test_clean_drops_invalid_ohlc_when_requested(invalid_ohlc_csv_path) -> None:
    df = CSVImporter().import_csv(invalid_ohlc_csv_path)
    cleaned = DataCleaner().clean(df, drop_invalid_ohlc=True)
    assert len(cleaned) == 2
    assert DataValidator().invalid_ohlc_mask(cleaned).sum() == 0


def test_clean_localizes_naive_timestamps(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    cleaned = DataCleaner().clean(df, tz="UTC")
    assert str(cleaned["Datetime"].dt.tz) == "UTC"
