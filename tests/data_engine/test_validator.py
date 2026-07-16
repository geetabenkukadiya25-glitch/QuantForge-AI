"""Tests for DataValidator."""

from app.data_engine.csv_importer import CSVImporter
from app.data_engine.validator import DataValidator


def test_valid_data_passes_validation(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    result = DataValidator().validate(df, timeframe="H1")
    assert result.is_valid
    assert result.duplicate_candles == 0
    assert result.invalid_ohlc_candles == 0
    assert result.missing_candles == 0


def test_duplicate_candles_detected(duplicate_csv_path) -> None:
    df = CSVImporter().import_csv(duplicate_csv_path)
    result = DataValidator().validate(df)
    assert result.duplicate_candles == 1
    assert not result.is_valid


def test_missing_values_detected(missing_values_csv_path) -> None:
    df = CSVImporter().import_csv(missing_values_csv_path)
    result = DataValidator().validate(df)
    assert result.missing_values["Open"] == 1
    assert not result.is_valid


def test_invalid_ohlc_detected(invalid_ohlc_csv_path) -> None:
    df = CSVImporter().import_csv(invalid_ohlc_csv_path)
    result = DataValidator().validate(df)
    assert result.invalid_ohlc_candles == 1
    assert not result.is_valid


def test_missing_candles_detected_with_gap(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    df = df.drop(df.index[2])  # remove the 02:00 candle, leaving a gap
    result = DataValidator().validate(df, timeframe="H1")
    assert result.missing_candles == 1
