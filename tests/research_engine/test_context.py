"""`ResearchContext`/`StrategyRecord`: the standardized research input."""

from app.research_engine.context import ResearchContext, StrategyRecord


def test_record_requires_strategy_model_and_backtest_result(record_b_bare) -> None:
    assert record_b_bare.strategy_model is not None
    assert record_b_bare.backtest_result is not None
    assert record_b_bare.optimization_result is None
    assert record_b_bare.validation_result is None
    assert record_b_bare.replay_result is None


def test_record_carries_optional_engine_outputs(record_a_full) -> None:
    assert record_a_full.optimization_result is not None
    assert record_a_full.validation_result is not None


def test_context_bundles_records_and_configuration(research_context, research_configuration) -> None:
    assert len(research_context.records) == 2
    assert research_context.configuration is research_configuration


def test_context_and_record_are_frozen_dataclasses(record_b_bare) -> None:
    import dataclasses

    assert dataclasses.is_dataclass(record_b_bare)
    try:
        record_b_bare.strategy_model = None  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except dataclasses.FrozenInstanceError:
        pass
