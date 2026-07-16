"""Tests for timeframe resampling (Timeframe Switch)."""

import pytest

from app.chart_engine.exceptions import ChartEngineError
from app.chart_engine.timeframe import resample_ohlcv


def test_resample_reduces_candle_count(hourly_df) -> None:
    resampled = resample_ohlcv(hourly_df, "H4")
    assert len(resampled) < len(hourly_df)
    assert len(resampled) == 18  # 72 hourly candles / 4


def test_resample_preserves_open_high_low_close_semantics(hourly_df) -> None:
    resampled = resample_ohlcv(hourly_df, "H4")
    first_bucket = hourly_df.iloc[:4]
    assert resampled["Open"].iloc[0] == first_bucket["Open"].iloc[0]
    assert resampled["Close"].iloc[0] == first_bucket["Close"].iloc[-1]
    assert resampled["High"].iloc[0] == first_bucket["High"].max()
    assert resampled["Low"].iloc[0] == first_bucket["Low"].min()


def test_resample_sums_volume(hourly_df) -> None:
    resampled = resample_ohlcv(hourly_df, "H4")
    first_bucket = hourly_df.iloc[:4]
    assert resampled["Volume"].iloc[0] == first_bucket["Volume"].sum()


def test_resample_unknown_timeframe_raises(hourly_df) -> None:
    with pytest.raises(ChartEngineError):
        resample_ohlcv(hourly_df, "M2")


def test_resample_without_volume_column_succeeds(minimal_df) -> None:
    resampled = resample_ohlcv(minimal_df, "H4")
    assert "Volume" not in resampled.columns
    assert len(resampled) >= 1
