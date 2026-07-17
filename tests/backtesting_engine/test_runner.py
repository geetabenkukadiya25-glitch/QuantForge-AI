"""`BacktestRunner`: full orchestration, both the raising and non-raising paths."""

import pytest

from app.backtesting_engine.exceptions import BacktestValidationError
from app.backtesting_engine.models import BacktestConfiguration
from app.backtesting_engine.runner import BacktestRunner, SessionStatus


def test_execute_returns_a_result(backtest_context) -> None:
    result = BacktestRunner().execute(backtest_context)
    assert result.checksum
    assert len(result.trades) > 0


def test_try_execute_never_raises_and_reports_success(backtest_context) -> None:
    session = BacktestRunner().try_execute(backtest_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None
    assert session.validation.is_valid


def test_execute_raises_on_invalid_context(strategy_model, ohlcv_data, indicator_engine, smart_money_engine) -> None:
    from app.backtesting_engine.context import BacktestContext

    bad_config = BacktestConfiguration(symbol="GBPUSD", timeframe="H1")  # not among the strategy's symbols
    context = BacktestContext(
        strategy_model=strategy_model,
        data=ohlcv_data,
        configuration=bad_config,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    with pytest.raises(BacktestValidationError):
        BacktestRunner().execute(context)


def test_try_execute_reports_failure_without_raising(strategy_model, ohlcv_data, indicator_engine, smart_money_engine) -> None:
    from app.backtesting_engine.context import BacktestContext

    bad_config = BacktestConfiguration(symbol="GBPUSD", timeframe="H1")
    context = BacktestContext(
        strategy_model=strategy_model,
        data=ohlcv_data,
        configuration=bad_config,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    session = BacktestRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert session.result is None
    assert not session.validation.is_valid
