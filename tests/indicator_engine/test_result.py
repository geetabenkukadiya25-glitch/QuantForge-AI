"""Tests for IndicatorResult."""

import json

import pytest

from app.indicator_engine.result import IndicatorResult


def _make_result(**overrides) -> IndicatorResult:
    defaults = dict(
        indicator_name="SMA",
        category="Moving Average",
        indicator_version="1.0.0",
        result_version="1.0.0",
        symbol="EURUSD",
        timeframe="H1",
        parameters={"window": 20},
        datetime_index=("2024-01-01T00:00:00", "2024-01-01T01:00:00"),
        values={"SMA": (1.0, 2.0)},
    )
    defaults.update(overrides)
    return IndicatorResult(**defaults)


def test_mismatched_output_length_raises() -> None:
    with pytest.raises(ValueError):
        _make_result(values={"SMA": (1.0, 2.0, 3.0)})


def test_to_dict_is_json_safe() -> None:
    result = _make_result()
    json.dumps(result.to_dict())  # must not raise


def test_to_dict_contains_expected_keys() -> None:
    result = _make_result()
    data = result.to_dict()
    assert data["indicator_name"] == "SMA"
    assert data["values"]["SMA"] == [1.0, 2.0]


def test_result_supports_none_values() -> None:
    result = _make_result(values={"SMA": (None, 2.0)})
    assert result.to_dict()["values"]["SMA"] == [None, 2.0]
