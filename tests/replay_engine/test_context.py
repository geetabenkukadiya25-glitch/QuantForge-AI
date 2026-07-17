"""`ReplayContext`: the only required input is historical OHLCV data."""

import pytest

from app.replay_engine.context import ReplayContext
from app.replay_engine.models import ReplayConfiguration


def test_context_requires_a_dataframe(replay_configuration: ReplayConfiguration) -> None:
    with pytest.raises(TypeError):
        ReplayContext(data=[1, 2, 3], configuration=replay_configuration)


def test_context_optional_fields_default_to_none(bare_replay_context) -> None:
    assert bare_replay_context.strategy_model is None
    assert bare_replay_context.indicator_engine is None
    assert bare_replay_context.smart_money_engine is None
    assert bare_replay_context.backtest_result is None


def test_context_carries_optional_visualization_inputs(replay_context) -> None:
    assert replay_context.strategy_model is not None
    assert replay_context.indicator_engine is not None
    assert replay_context.smart_money_engine is not None
    assert replay_context.backtest_result is not None
