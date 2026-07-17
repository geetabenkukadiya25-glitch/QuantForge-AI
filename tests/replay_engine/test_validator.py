"""Pre-execution validation for a `ReplayContext`."""

import dataclasses

import pandas as pd

from app.replay_engine.context import ReplayContext
from app.replay_engine.models import ReplayConfiguration
from app.replay_engine.validator import ReplayValidator


def test_bare_context_is_valid(bare_replay_context) -> None:
    result = ReplayValidator().validate(bare_replay_context)
    assert result.is_valid


def test_full_context_is_valid(replay_context) -> None:
    result = ReplayValidator().validate(replay_context)
    assert result.is_valid


def test_missing_required_column_is_rejected(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1] * 5})
    context = ReplayContext(data=data, configuration=replay_configuration)
    result = ReplayValidator().validate(context)
    assert not result.is_valid
    assert any("columns" in issue.path for issue in result.errors)


def test_unsorted_datetimes_are_rejected(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({
        "Datetime": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-01")],
        "Open": [1.0, 1.0], "High": [1.1, 1.1], "Low": [0.9, 0.9], "Close": [1.0, 1.0],
    })
    context = ReplayContext(data=data, configuration=replay_configuration)
    result = ReplayValidator().validate(context)
    assert not result.is_valid


def test_duplicate_timestamps_are_rejected(replay_configuration: ReplayConfiguration) -> None:
    ts = pd.Timestamp("2024-01-01")
    data = pd.DataFrame({"Datetime": [ts, ts], "Open": [1.0, 1.0], "High": [1.1, 1.1], "Low": [0.9, 0.9], "Close": [1.0, 1.0]})
    context = ReplayContext(data=data, configuration=replay_configuration)
    result = ReplayValidator().validate(context)
    assert not result.is_valid


def test_start_index_out_of_range_is_rejected(ohlcv_data: pd.DataFrame) -> None:
    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=len(ohlcv_data) + 5)
    context = ReplayContext(data=ohlcv_data, configuration=config)
    result = ReplayValidator().validate(context)
    assert not result.is_valid
    assert any("start_index" in issue.path for issue in result.errors)


def test_end_index_before_start_index_is_rejected(ohlcv_data: pd.DataFrame) -> None:
    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=10, end_index=5)
    context = ReplayContext(data=ohlcv_data, configuration=config)
    result = ReplayValidator().validate(context)
    assert not result.is_valid


def test_high_less_than_low_is_rejected(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=3, freq="h"),
        "Open": [1.0, 1.0, 1.0], "High": [0.5, 1.1, 1.1], "Low": [0.9, 0.9, 0.9], "Close": [1.0, 1.0, 1.0],
    })
    context = ReplayContext(data=data, configuration=replay_configuration)
    result = ReplayValidator().validate(context)
    assert not result.is_valid
    assert any("High < Low" in issue.message for issue in result.errors)


def test_indicators_without_indicator_engine_is_rejected(replay_context) -> None:
    context = dataclasses.replace(replay_context, indicator_engine=None)
    result = ReplayValidator().validate(context)
    assert not result.is_valid


def test_report_lists_every_error() -> None:
    from app.replay_engine.validator import ReplayCheckResult, ReplayIssue

    result = ReplayCheckResult(errors=[ReplayIssue(path="a", message="bad")])
    assert "FAILED" in result.report()
    assert "a: bad" in result.report()
