"""End-to-end determinism tests: same input must always produce identical
generated EA source AND an identical checksum -- the core guarantee this
engine's docstrings promise."""

from app.ea_generator.engine import EAGeneratorEngine


def test_bare_context_is_fully_deterministic(strategy_model_a, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    first = engine.execute(strategy_model_a, ea_configuration)
    second = engine.execute(strategy_model_a, ea_configuration)
    assert first.checksum == second.checksum
    assert first.source_code == second.source_code


def test_full_context_is_fully_deterministic(strategy_model_a, ea_configuration, validation_result_a, optimization_result_a, research_result_a, portfolio_result_a) -> None:
    engine = EAGeneratorEngine()
    kwargs = dict(validation_result=validation_result_a, optimization_result=optimization_result_a, research_result=research_result_a, portfolio_result=portfolio_result_a)
    first = engine.execute(strategy_model_a, ea_configuration, **kwargs)
    second = engine.execute(strategy_model_a, ea_configuration, **kwargs)
    assert first.checksum == second.checksum
    assert first.source_code == second.source_code


def test_different_strategies_produce_different_checksums(strategy_model_a, strategy_model_b, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    result_a = engine.execute(strategy_model_a, ea_configuration)
    result_b = engine.execute(strategy_model_b, ea_configuration)
    assert result_a.checksum != result_b.checksum
    assert result_a.source_code != result_b.source_code


def test_different_configurations_produce_different_checksums(strategy_model_a) -> None:
    from app.ea_generator.models import EAGeneratorConfiguration

    engine = EAGeneratorEngine()
    result_a = engine.execute(strategy_model_a, EAGeneratorConfiguration(lot_size=0.1))
    result_b = engine.execute(strategy_model_a, EAGeneratorConfiguration(lot_size=0.2))
    assert result_a.checksum != result_b.checksum


def test_repeated_generation_ten_times_is_stable(strategy_model_a, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    checksums = {engine.execute(strategy_model_a, ea_configuration).checksum for _ in range(10)}
    assert len(checksums) == 1


def test_repeated_generation_source_text_is_byte_identical(strategy_model_a, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    sources = {engine.execute(strategy_model_a, ea_configuration).source_code for _ in range(5)}
    assert len(sources) == 1


def test_result_ids_are_unique_even_when_checksum_matches(strategy_model_a, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    first = engine.execute(strategy_model_a, ea_configuration)
    second = engine.execute(strategy_model_a, ea_configuration)
    assert first.checksum == second.checksum
    assert first.result_id != second.result_id
    assert first.metadata.ea_id != second.metadata.ea_id
