"""Tests for app.ea_generator.runner."""

import pytest

from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.exceptions import EAValidationError
from app.ea_generator.models import EAGeneratorConfiguration
from app.ea_generator.runner import EAGeneratorRunner, SessionStatus


def test_try_execute_succeeds_for_valid_context(ea_context) -> None:
    session = EAGeneratorRunner().try_execute(ea_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_try_execute_never_raises_on_invalid_context(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="bad.txt"))
    session = EAGeneratorRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert session.result is None


def test_execute_returns_result_for_valid_context(ea_context) -> None:
    result = EAGeneratorRunner().execute(ea_context)
    assert result.source_code


def test_execute_raises_for_invalid_context(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="bad.txt"))
    with pytest.raises(EAValidationError):
        EAGeneratorRunner().execute(context)


def test_validation_error_carries_issues(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="bad.txt"))
    with pytest.raises(EAValidationError) as exc_info:
        EAGeneratorRunner().execute(context)
    assert len(exc_info.value.issues) > 0


def test_session_has_started_and_completed_timestamps(ea_context) -> None:
    session = EAGeneratorRunner().try_execute(ea_context)
    assert session.started_at is not None
    assert session.completed_at is not None
    assert session.completed_at >= session.started_at


def test_session_id_is_unique_per_call(ea_context) -> None:
    runner = EAGeneratorRunner()
    first = runner.try_execute(ea_context)
    second = runner.try_execute(ea_context)
    assert first.session_id != second.session_id


def test_run_delegates_to_execute(ea_context) -> None:
    runner = EAGeneratorRunner()
    result_via_run = runner.run(ea_context)
    result_via_execute = runner.execute(ea_context)
    assert result_via_run.checksum == result_via_execute.checksum


def test_full_context_generation_succeeds(full_ea_context) -> None:
    session = EAGeneratorRunner().try_execute(full_ea_context)
    assert session.is_successful
