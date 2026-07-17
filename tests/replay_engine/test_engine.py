"""`ReplayEngine`: the top-level facade -- execute/try_execute/create_controller."""

import pytest

from app.replay_engine.controller import ReplayController
from app.replay_engine.engine import ReplayEngine
from app.replay_engine.exceptions import ReplayValidationError
from app.replay_engine.runner import ReplaySession


def test_execute_returns_a_replay_result(ohlcv_data, replay_configuration, base_strategy_model, indicator_engine, smart_money_engine, backtest_result) -> None:
    engine = ReplayEngine()
    result = engine.execute(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    assert result.result_id
    assert result.metadata.strategy_id == base_strategy_model.metadata.id


def test_try_execute_returns_a_session(ohlcv_data, replay_configuration) -> None:
    engine = ReplayEngine()
    session = engine.try_execute(ohlcv_data, replay_configuration)
    assert isinstance(session, ReplaySession)
    assert session.is_successful


def test_create_controller_returns_a_working_controller(ohlcv_data, replay_configuration, base_strategy_model, indicator_engine, smart_money_engine, backtest_result) -> None:
    engine = ReplayEngine()
    controller = engine.create_controller(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    assert isinstance(controller, ReplayController)
    controller.play()
    controller.step_forward(3)
    assert controller.cursor.index == 3


def test_execute_never_optimizes_never_backtests(ohlcv_data, replay_configuration) -> None:
    """Bare data-only execution succeeds -- proving Replay never re-invokes
    Strategy Builder/Optimization/Backtesting logic of its own."""
    engine = ReplayEngine()
    result = engine.execute(ohlcv_data, replay_configuration)
    assert result.metadata.strategy_id is None
    assert result.metadata.backtest_result_id is None


def test_run_aliases_execute(ohlcv_data, replay_configuration) -> None:
    engine = ReplayEngine()
    result = engine.run(ohlcv_data, replay_configuration)
    assert result.result_id


def test_execute_raises_on_invalid_configuration(ohlcv_data) -> None:
    from app.replay_engine.models import ReplayConfiguration

    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=len(ohlcv_data) + 10)
    engine = ReplayEngine()
    with pytest.raises(ReplayValidationError):
        engine.execute(ohlcv_data, config)
