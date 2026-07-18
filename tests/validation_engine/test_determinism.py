"""Determinism: two `ValidationEngine.execute()` calls over the same
inputs must produce the same checksum -- proving no random identity
field leaked into the checksummed payload (the recurring bug class
caught in Phases 9-11).
"""

from app.validation_engine.engine import ValidationEngine


def test_two_runs_of_the_same_inputs_produce_the_same_checksum(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration, indicator_engine, smart_money_engine
) -> None:
    engine = ValidationEngine(indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    result1 = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    result2 = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.validation_id != result2.metadata.validation_id


def test_scores_are_identical_across_runs(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration, indicator_engine, smart_money_engine
) -> None:
    engine = ValidationEngine(indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    result1 = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    result2 = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    assert result1.robustness_score == result2.robustness_score
    assert result1.confidence_score == result2.confidence_score
    assert result1.stability_score == result2.stability_score


def test_checksum_changes_when_the_candidate_changes(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, walk_forward_configuration, monte_carlo_configuration, indicator_engine, smart_money_engine
) -> None:
    from app.validation_engine.models import ValidationConfiguration

    engine = ValidationEngine(indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    configuration_a = ValidationConfiguration(
        strategy_id=base_strategy_model.metadata.id, symbol="EURUSD", timeframe="H1",
        run_walk_forward=True, run_monte_carlo=False, walk_forward=walk_forward_configuration,
    )
    configuration_b = ValidationConfiguration(
        strategy_id=base_strategy_model.metadata.id, symbol="EURUSD", timeframe="H1",
        run_walk_forward=True, run_monte_carlo=True, walk_forward=walk_forward_configuration, monte_carlo=monte_carlo_configuration,
    )
    result_a = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, configuration_a)
    result_b = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, configuration_b)
    assert result_a.checksum != result_b.checksum
