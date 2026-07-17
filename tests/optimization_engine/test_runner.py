"""`OptimizationRunner`: full orchestration, both the raising and non-raising paths."""

import dataclasses

import pytest

from app.optimization_engine.exceptions import OptimizationValidationError
from app.optimization_engine.models import (
    Objective,
    OptimizationConfiguration,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.optimization_engine.runner import OptimizationRunner, SessionStatus


def test_execute_returns_a_result(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    assert result.checksum
    assert len(result.candidates) > 0
    assert result.statistics.evaluated_candidates == len(result.candidates)


def test_try_execute_never_raises_and_reports_success(optimization_context) -> None:
    session = OptimizationRunner().try_execute(optimization_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_raises_on_invalid_context(optimization_context) -> None:
    bad_config = OptimizationConfiguration(
        strategy_id=optimization_context.configuration.strategy_id, symbol="GBPUSD", timeframe="H1",
        search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT,
    )
    context = dataclasses.replace(optimization_context, configuration=bad_config)
    with pytest.raises(OptimizationValidationError):
        OptimizationRunner().execute(context)


def test_try_execute_reports_failure_without_raising(optimization_context) -> None:
    bad_config = OptimizationConfiguration(
        strategy_id=optimization_context.configuration.strategy_id, symbol="GBPUSD", timeframe="H1",
        search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT,
    )
    context = dataclasses.replace(optimization_context, configuration=bad_config)
    session = OptimizationRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert session.result is None


def test_best_candidate_has_rank_one(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    best_entries = [e for e in result.history.entries if e.rank == 1]
    assert len(best_entries) == 1
    assert best_entries[0].candidate_id == result.best_candidate_id
    assert result.statistics.best_candidate_id == result.best_candidate_id


def test_candidate_level_failure_does_not_abort_the_run(optimization_context) -> None:
    # take_profit_points has a `ge=0` constraint on BacktestConfiguration --
    # a negative candidate value fails Pydantic validation for that one
    # candidate only, without aborting the whole optimization run.
    space = ParameterSpace(
        definitions=(
            ParameterDefinition(
                name="configuration.take_profit_points", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FLOAT,
                min_value=-2.0, max_value=2.0, step=4.0,
            ),
        )
    )
    context = dataclasses.replace(optimization_context, parameter_space=space)
    result = OptimizationRunner().execute(context)
    assert result.statistics.failed_candidates >= 1
    assert result.statistics.evaluated_candidates >= 1
    failed = [e for e in result.history.entries if not e.succeeded]
    assert all(e.error_message for e in failed)
