"""`BacktestSerializer`."""

import json

import yaml

from app.backtesting_engine.runner import BacktestRunner
from app.backtesting_engine.serializer import BacktestSerializer


def test_to_dict_round_trips_key_fields(backtest_context) -> None:
    result = BacktestRunner().execute(backtest_context)
    data = BacktestSerializer().to_dict(result)
    assert data["checksum"] == result.checksum
    assert data["result_id"] == result.result_id
    assert len(data["trades"]) == len(result.trades)


def test_to_json_is_valid_json(backtest_context) -> None:
    result = BacktestRunner().execute(backtest_context)
    text = BacktestSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_sorted_and_compact(backtest_context) -> None:
    result = BacktestRunner().execute(backtest_context)
    text = BacktestSerializer().to_json(result, canonical=True)
    assert "\n" not in text
    assert json.loads(text)["checksum"] == result.checksum


def test_to_yaml_is_valid_yaml(backtest_context) -> None:
    result = BacktestRunner().execute(backtest_context)
    text = BacktestSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum
