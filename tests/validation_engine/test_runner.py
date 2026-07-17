"""`ValidationRunner`: full orchestration, both the raising and non-raising paths."""

import dataclasses

import pytest

from app.validation_engine.exceptions import ValidationValidationError
from app.validation_engine.runner import SessionStatus, ValidationRunner


def test_execute_returns_a_result(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    assert result.checksum
    assert result.walk_forward_result is not None
    assert result.monte_carlo_result is not None
    assert result.robustness_score is not None
    assert result.confidence_score is not None
    assert result.stability_score is not None


def test_try_execute_never_raises_and_reports_success(validation_context) -> None:
    session = ValidationRunner().try_execute(validation_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED


def test_execute_raises_on_invalid_context(validation_context) -> None:
    context = dataclasses.replace(validation_context, candidate_id="nonexistent")
    with pytest.raises(ValidationValidationError):
        ValidationRunner().execute(context)


def test_try_execute_reports_failure_without_raising(validation_context) -> None:
    context = dataclasses.replace(validation_context, candidate_id="nonexistent")
    session = ValidationRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert session.result is None


def test_walk_forward_only_skips_monte_carlo(validation_context) -> None:
    config = validation_context.configuration.model_copy(update={"run_monte_carlo": False, "monte_carlo": None})
    context = dataclasses.replace(validation_context, configuration=config)
    result = ValidationRunner().execute(context)
    assert result.walk_forward_result is not None
    assert result.monte_carlo_result is None
    assert result.confidence_score is None


def test_monte_carlo_only_skips_walk_forward(validation_context) -> None:
    config = validation_context.configuration.model_copy(update={"run_walk_forward": False, "walk_forward": None})
    context = dataclasses.replace(validation_context, configuration=config)
    result = ValidationRunner().execute(context)
    assert result.walk_forward_result is None
    assert result.monte_carlo_result is not None
    assert result.robustness_score is None
    assert result.stability_score is not None  # still computed via parameter_stability alone
