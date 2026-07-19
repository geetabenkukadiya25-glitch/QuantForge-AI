"""`app.ui.dataset_detection`: presentation-layer Symbol/Timeframe
auto-detection for the Backtesting Dashboard's Execution Assumptions
panel. Pure functions -- no Streamlit runtime required."""

import pandas as pd
import pytest

from app.ui.dataset_detection import (
    UNKNOWN,
    detect_mismatch,
    detect_symbol,
    detect_symbol_from_filename,
    detect_timeframe,
    detect_timeframe_from_datetime,
    detect_timeframe_from_filename,
)
from app.ui.state import DatasetMetadata

# ---------------------------------------------------------------------
# Filename detection -- symbol
# ---------------------------------------------------------------------


def test_symbol_from_filename_xau_alias() -> None:
    assert detect_symbol_from_filename("XAU_5m_data.csv") == "XAUUSD"


def test_symbol_from_filename_six_letter_pair() -> None:
    assert detect_symbol_from_filename("EURUSD_H1.csv") == "EURUSD"


def test_symbol_from_filename_lowercase() -> None:
    assert detect_symbol_from_filename("gbpjpy_m30_export.csv") == "GBPJPY"


def test_symbol_from_filename_crypto_alias() -> None:
    assert detect_symbol_from_filename("btc_1h.csv") == "BTCUSD"


def test_symbol_from_filename_index_alias() -> None:
    assert detect_symbol_from_filename("US30_daily.csv") == "US30"


def test_symbol_from_filename_no_match_returns_none() -> None:
    assert detect_symbol_from_filename("data_export_final.csv") is None


def test_symbol_from_filename_none_input_returns_none() -> None:
    assert detect_symbol_from_filename(None) is None


def test_symbol_from_filename_empty_string_returns_none() -> None:
    assert detect_symbol_from_filename("") is None


def test_symbol_from_filename_first_matching_token_wins() -> None:
    """"XAU_5m_data.csv" must resolve via the "XAU" alias, not be
    confused by the "5m" timeframe token."""
    assert detect_symbol_from_filename("XAU_5m_data.csv") == "XAUUSD"


# ---------------------------------------------------------------------
# Filename detection -- timeframe
# ---------------------------------------------------------------------


def test_timeframe_from_filename_minutes_shorthand() -> None:
    assert detect_timeframe_from_filename("XAU_5m_data.csv") == "M5"


def test_timeframe_from_filename_standard_label_uppercase() -> None:
    assert detect_timeframe_from_filename("EURUSD_H1.csv") == "H1"


def test_timeframe_from_filename_standard_label_lowercase() -> None:
    assert detect_timeframe_from_filename("eurusd_m15_export.csv") == "M15"


def test_timeframe_from_filename_hour_shorthand() -> None:
    assert detect_timeframe_from_filename("gbpusd_4h.csv") == "H4"


def test_timeframe_from_filename_day_shorthand() -> None:
    assert detect_timeframe_from_filename("audusd_1d.csv") == "D1"


def test_timeframe_from_filename_min_word_form() -> None:
    assert detect_timeframe_from_filename("nzdusd_30min.csv") == "M30"


def test_timeframe_from_filename_no_match_returns_none() -> None:
    assert detect_timeframe_from_filename("historical_prices.csv") is None


def test_timeframe_from_filename_none_input_returns_none() -> None:
    assert detect_timeframe_from_filename(None) is None


def test_timeframe_from_filename_empty_string_returns_none() -> None:
    assert detect_timeframe_from_filename("") is None


# ---------------------------------------------------------------------
# Datetime-spacing detection (delegates to app.data_engine.TimeframeConverter)
# ---------------------------------------------------------------------


def _ohlcv(freq: str, periods: int = 20) -> pd.DataFrame:
    dt = pd.date_range("2024-01-01", periods=periods, freq=freq)
    return pd.DataFrame({"Datetime": dt, "Open": 1.0, "High": 1.1, "Low": 0.9, "Close": 1.0, "Volume": 100})


def test_timeframe_from_datetime_detects_5_minute_spacing() -> None:
    assert detect_timeframe_from_datetime(_ohlcv("5min")) == "M5"


def test_timeframe_from_datetime_detects_1_hour_spacing() -> None:
    assert detect_timeframe_from_datetime(_ohlcv("1h")) == "H1"


def test_timeframe_from_datetime_detects_daily_spacing() -> None:
    assert detect_timeframe_from_datetime(_ohlcv("1D")) == "D1"


def test_timeframe_from_datetime_none_dataframe_returns_none() -> None:
    assert detect_timeframe_from_datetime(None) is None


def test_timeframe_from_datetime_single_row_returns_none() -> None:
    df = pd.DataFrame({"Datetime": [pd.Timestamp("2024-01-01")], "Open": [1.0]})
    assert detect_timeframe_from_datetime(df) is None


def test_timeframe_from_datetime_missing_datetime_column_returns_none() -> None:
    """Must never raise -- a DataFrame without a Datetime column is a
    legitimate fallback case (e.g. malformed upload), not a crash."""
    df = pd.DataFrame({"Open": [1.0, 2.0]})
    assert detect_timeframe_from_datetime(df) is None


# ---------------------------------------------------------------------
# Full priority chain -- detect_symbol
# ---------------------------------------------------------------------


def test_detect_symbol_prefers_metadata_over_filename() -> None:
    metadata = DatasetMetadata(filename="XAU_5m_data.csv", symbol="XAUUSD_FROM_METADATA")
    assert detect_symbol(metadata, "XAU_5m_data.csv", None) == "XAUUSD_FROM_METADATA"


def test_detect_symbol_falls_back_to_filename_when_metadata_symbol_missing() -> None:
    metadata = DatasetMetadata(filename="XAU_5m_data.csv")
    assert detect_symbol(metadata, "XAU_5m_data.csv", None) == "XAUUSD"


def test_detect_symbol_falls_back_to_dataframe_attrs() -> None:
    df = pd.DataFrame({"Open": [1.0]})
    df.attrs["symbol"] = "GBPUSD"
    assert detect_symbol(None, "unrecognizable_file.csv", df) == "GBPUSD"


def test_detect_symbol_unknown_when_everything_fails() -> None:
    df = pd.DataFrame({"Open": [1.0]})
    assert detect_symbol(None, "unrecognizable_file.csv", df) == UNKNOWN


def test_detect_symbol_unknown_when_no_metadata_no_filename_no_df() -> None:
    assert detect_symbol(None, None, None) == UNKNOWN


def test_detect_symbol_metadata_none_symbol_falls_through() -> None:
    metadata = DatasetMetadata(filename="a.csv", symbol=None)
    assert detect_symbol(metadata, "EURUSD_H1.csv", None) == "EURUSD"


# ---------------------------------------------------------------------
# Full priority chain -- detect_timeframe
# ---------------------------------------------------------------------


def test_detect_timeframe_prefers_metadata_over_filename() -> None:
    metadata = DatasetMetadata(filename="XAU_5m_data.csv", timeframe="H4")
    assert detect_timeframe(metadata, "XAU_5m_data.csv", None) == "H4"


def test_detect_timeframe_falls_back_to_filename_when_metadata_timeframe_missing() -> None:
    metadata = DatasetMetadata(filename="XAU_5m_data.csv")
    assert detect_timeframe(metadata, "XAU_5m_data.csv", None) == "M5"


def test_detect_timeframe_falls_back_to_metadata_statistics() -> None:
    metadata = DatasetMetadata(filename="unrecognizable.csv", statistics={"detected_timeframe": "H4"})
    assert detect_timeframe(metadata, "unrecognizable.csv", None) == "H4"


def test_detect_timeframe_falls_back_to_datetime_spacing() -> None:
    df = _ohlcv("15min")
    assert detect_timeframe(None, "unrecognizable.csv", df) == "M15"


def test_detect_timeframe_unknown_when_everything_fails() -> None:
    df = pd.DataFrame({"Open": [1.0]})
    assert detect_timeframe(None, "unrecognizable.csv", df) == UNKNOWN


def test_detect_timeframe_unknown_when_no_metadata_no_filename_no_df() -> None:
    assert detect_timeframe(None, None, None) == UNKNOWN


# ---------------------------------------------------------------------
# The example from the task's requirements, end to end
# ---------------------------------------------------------------------


def test_xau_5m_example_end_to_end() -> None:
    filename = "XAU_5m_data.csv"
    assert detect_symbol(None, filename, None) == "XAUUSD"
    assert detect_timeframe(None, filename, None) == "M5"


# ---------------------------------------------------------------------
# Strategy / dataset mismatch detection
# ---------------------------------------------------------------------


def test_mismatch_detected_when_symbol_and_timeframe_both_differ() -> None:
    mismatch = detect_mismatch(("EURUSD",), ("M15",), "XAUUSD", "M5")
    assert mismatch is not None
    assert mismatch.symbol_mismatch is True
    assert mismatch.timeframe_mismatch is True
    assert mismatch.strategy_symbols == ("EURUSD",)
    assert mismatch.strategy_timeframes == ("M15",)
    assert mismatch.dataset_symbol == "XAUUSD"
    assert mismatch.dataset_timeframe == "M5"


def test_mismatch_detected_when_only_symbol_differs() -> None:
    mismatch = detect_mismatch(("EURUSD",), ("M15",), "XAUUSD", "M15")
    assert mismatch is not None
    assert mismatch.symbol_mismatch is True
    assert mismatch.timeframe_mismatch is False


def test_mismatch_detected_when_only_timeframe_differs() -> None:
    mismatch = detect_mismatch(("EURUSD",), ("M15",), "EURUSD", "M5")
    assert mismatch is not None
    assert mismatch.symbol_mismatch is False
    assert mismatch.timeframe_mismatch is True


def test_no_mismatch_when_both_match() -> None:
    assert detect_mismatch(("EURUSD",), ("M15",), "EURUSD", "M15") is None


def test_no_mismatch_when_symbol_matches_one_of_several_declared() -> None:
    assert detect_mismatch(("EURUSD", "GBPUSD"), ("M15", "H1"), "GBPUSD", "H1") is None


def test_no_mismatch_when_dataset_symbol_unknown() -> None:
    assert detect_mismatch(("EURUSD",), ("M15",), UNKNOWN, "M5") is None


def test_no_mismatch_when_dataset_timeframe_unknown() -> None:
    assert detect_mismatch(("EURUSD",), ("M15",), "XAUUSD", UNKNOWN) is None


def test_no_mismatch_when_both_unknown() -> None:
    assert detect_mismatch(("EURUSD",), ("M15",), UNKNOWN, UNKNOWN) is None
