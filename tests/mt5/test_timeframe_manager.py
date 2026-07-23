"""`timeframe_manager.py` -- pure lookup table."""

import pytest

from app.mt5.timeframe_manager import supported_timeframes, to_mt5_timeframe


def test_h1_matches_metatrader5_constant() -> None:
    assert to_mt5_timeframe("H1") == (1 | 0x4000)


def test_d1_matches_metatrader5_constant() -> None:
    assert to_mt5_timeframe("D1") == (24 | 0x4000)


def test_case_insensitive() -> None:
    assert to_mt5_timeframe("m1") == to_mt5_timeframe("M1")


def test_unknown_timeframe_raises_value_error() -> None:
    with pytest.raises(ValueError):
        to_mt5_timeframe("M7")


def test_supported_timeframes_nonempty() -> None:
    assert "H1" in supported_timeframes()
    assert "D1" in supported_timeframes()
