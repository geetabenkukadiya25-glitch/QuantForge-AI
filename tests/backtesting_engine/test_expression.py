"""The safe rule-condition evaluator."""

import pytest

from app.backtesting_engine.exceptions import BacktestExecutionError
from app.backtesting_engine.expression import evaluate_condition


def test_evaluates_simple_comparison() -> None:
    assert evaluate_condition("close > open", {"close": 10, "open": 5}) is True
    assert evaluate_condition("close > open", {"close": 5, "open": 10}) is False


def test_evaluates_boolean_combinators() -> None:
    ns = {"a": 1, "b": 2, "c": 3}
    assert evaluate_condition("a < b and b < c", ns) is True
    assert evaluate_condition("a > b or b < c", ns) is True
    assert evaluate_condition("not (a > b)", ns) is True


def test_evaluates_arithmetic() -> None:
    assert evaluate_condition("close - open > 1", {"close": 10, "open": 8}) is True


def test_allows_whitelisted_calls() -> None:
    assert evaluate_condition("abs(close - open) > 1", {"close": 5, "open": 10}) is True
    assert evaluate_condition("max(a, b) == b", {"a": 1, "b": 2}) is True


def test_none_comparison_is_false_not_error() -> None:
    assert evaluate_condition("value > 1", {"value": None}) is False


def test_rejects_unknown_name() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("unknown_indicator > 1", {})


def test_rejects_invalid_syntax() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("fast_ma crosses above slow_ma", {"fast_ma": 1, "slow_ma": 2})


def test_rejects_empty_condition() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("", {})


def test_rejects_disallowed_function_call() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("__import__('os').system('echo hi')", {})


def test_rejects_attribute_access() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("close.real", {"close": 1.0})


def test_rejects_subscript_access() -> None:
    with pytest.raises(BacktestExecutionError):
        evaluate_condition("close[0]", {"close": [1.0]})
