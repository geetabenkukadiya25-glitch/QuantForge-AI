"""Tests for the DataLoader facade."""

from app.data_engine.exceptions import CSVFormatError
from app.data_engine.loader import DataLoader

import pytest


def test_load_csv_returns_cleaned_dataframe(duplicate_csv_path) -> None:
    df = DataLoader().load_csv(duplicate_csv_path)
    assert len(df) == 2  # duplicate removed by default cleaning


def test_load_csv_without_cleaning_keeps_duplicates(duplicate_csv_path) -> None:
    df = DataLoader().load_csv(duplicate_csv_path, clean=False)
    assert len(df) == 3


def test_load_csv_corrupted_raises(corrupted_csv_path) -> None:
    with pytest.raises(CSVFormatError):
        DataLoader().load_csv(corrupted_csv_path)


def test_preview_head_and_tail(valid_csv_path) -> None:
    loader = DataLoader()
    df = loader.load_csv(valid_csv_path)
    assert len(loader.preview_head(df, n=2)) == 2
    assert len(loader.preview_tail(df, n=2)) == 2


def test_statistics_contents(valid_csv_path) -> None:
    loader = DataLoader()
    df = loader.load_csv(valid_csv_path)
    stats = loader.statistics(df)
    assert stats["num_candles"] == 5
    assert stats["detected_timeframe"] == "H1"
    assert stats["missing_candles"] == 0
    assert stats["duplicate_candles"] == 0
    assert stats["memory_usage_bytes"] > 0
