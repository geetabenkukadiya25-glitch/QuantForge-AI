"""Tests for app.ea_generator.engine."""

import pytest

from app.core.base_engine import BaseEngine
from app.ea_generator.engine import EAGeneratorEngine
from app.ea_generator.exceptions import EAValidationError
from app.ea_generator.models import EAGeneratorConfiguration


def test_engine_is_a_base_engine() -> None:
    assert isinstance(EAGeneratorEngine(), BaseEngine)


def test_execute_returns_result(strategy_model_a, ea_configuration) -> None:
    result = EAGeneratorEngine().execute(strategy_model_a, ea_configuration)
    assert result.source_code
    assert result.metadata.strategy_id == strategy_model_a.metadata.id


def test_execute_raises_on_invalid_configuration(strategy_model_a) -> None:
    with pytest.raises(EAValidationError):
        EAGeneratorEngine().execute(strategy_model_a, EAGeneratorConfiguration(output_filename="bad.txt"))


def test_try_execute_never_raises(strategy_model_a) -> None:
    session = EAGeneratorEngine().try_execute(strategy_model_a, EAGeneratorConfiguration(output_filename="bad.txt"))
    assert not session.is_successful


def test_try_execute_succeeds_for_valid_input(strategy_model_a, ea_configuration) -> None:
    session = EAGeneratorEngine().try_execute(strategy_model_a, ea_configuration)
    assert session.is_successful


def test_run_aliases_execute(strategy_model_a, ea_configuration) -> None:
    engine = EAGeneratorEngine()
    via_run = engine.run(strategy_model_a, ea_configuration)
    via_execute = engine.execute(strategy_model_a, ea_configuration)
    assert via_run.checksum == via_execute.checksum


def test_execute_with_every_optional_artifact(strategy_model_a, ea_configuration, validation_result_a, optimization_result_a, research_result_a, portfolio_result_a) -> None:
    result = EAGeneratorEngine().execute(
        strategy_model_a,
        ea_configuration,
        validation_result=validation_result_a,
        optimization_result=optimization_result_a,
        research_result=research_result_a,
        portfolio_result=portfolio_result_a,
    )
    assert result.source_code


def test_engine_accepts_custom_runner(strategy_model_a, ea_configuration) -> None:
    from app.ea_generator.runner import EAGeneratorRunner

    engine = EAGeneratorEngine(runner=EAGeneratorRunner())
    result = engine.execute(strategy_model_a, ea_configuration)
    assert result.source_code


def test_two_engines_produce_identical_checksum(strategy_model_a, ea_configuration) -> None:
    result_a = EAGeneratorEngine().execute(strategy_model_a, ea_configuration)
    result_b = EAGeneratorEngine().execute(strategy_model_a, ea_configuration)
    assert result_a.checksum == result_b.checksum
