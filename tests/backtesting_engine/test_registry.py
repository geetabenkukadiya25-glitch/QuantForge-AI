"""`BacktestRegistry`."""

import pytest

from app.backtesting_engine.exceptions import BacktestDisabledError, BacktestNotFoundError, BacktestRegistrationError
from app.backtesting_engine.registry import BacktestRegistry
from app.backtesting_engine.runner import BacktestRunner


def _result(backtest_context):
    return BacktestRunner().execute(backtest_context)


def test_register_and_load(backtest_context) -> None:
    registry = BacktestRegistry()
    result = _result(backtest_context)
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(backtest_context) -> None:
    registry = BacktestRegistry()
    result = _result(backtest_context)
    registry.register(result)
    with pytest.raises(BacktestRegistrationError):
        registry.register(result)


def test_load_unknown_raises(backtest_context) -> None:
    registry = BacktestRegistry()
    with pytest.raises(BacktestNotFoundError):
        registry.load("unknown-id")


def test_disable_and_require_enabled(backtest_context) -> None:
    registry = BacktestRegistry()
    result = _result(backtest_context)
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(BacktestDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_search_by_strategy_id(backtest_context) -> None:
    registry = BacktestRegistry()
    result = _result(backtest_context)
    registry.register(result)
    matches = registry.search(strategy_id=result.metadata.strategy_id)
    assert len(matches) == 1
    assert registry.search(strategy_id="nonexistent") == []
