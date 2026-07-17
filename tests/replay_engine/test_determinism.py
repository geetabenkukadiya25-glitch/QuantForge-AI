"""Determinism: two `ReplayEngine.execute()` calls over the same context must
produce the same checksum -- proving no random identity field leaked into
the checksummed payload (the recurring bug class caught in Phases 9-11).
"""

from app.replay_engine.engine import ReplayEngine


def test_two_runs_of_the_same_context_produce_the_same_checksum(ohlcv_data, replay_configuration, base_strategy_model, indicator_engine, smart_money_engine, backtest_result) -> None:
    engine = ReplayEngine()
    result1 = engine.execute(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    result2 = engine.execute(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.replay_id != result2.metadata.replay_id


def test_timeline_and_statistics_are_identical_across_runs(ohlcv_data, replay_configuration, base_strategy_model, indicator_engine, smart_money_engine, backtest_result) -> None:
    engine = ReplayEngine()
    result1 = engine.execute(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    result2 = engine.execute(
        ohlcv_data, replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )
    assert result1.timeline == result2.timeline
    assert result1.statistics == result2.statistics


def test_data_checksum_changes_when_the_scope_changes(ohlcv_data, base_strategy_model, indicator_engine, smart_money_engine, backtest_result) -> None:
    from app.replay_engine.models import ReplayConfiguration

    engine = ReplayEngine()
    full = engine.execute(ohlcv_data, ReplayConfiguration(symbol="EURUSD", timeframe="H1"))
    scoped = engine.execute(ohlcv_data, ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=5, end_index=50))
    assert full.metadata.data_checksum != scoped.metadata.data_checksum
