"""`GridSearchOptimizer` and `RandomSearchOptimizer`."""

import pytest

from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.models import (
    Objective,
    OptimizationConfiguration,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.optimization_engine.search import GridSearchOptimizer, RandomSearchOptimizer


def _space() -> ParameterSpace:
    return ParameterSpace(
        definitions=(
            ParameterDefinition(name="a", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.INTEGER, min_value=1, max_value=3, step=1),
            ParameterDefinition(name="b", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.BOOLEAN),
        )
    )


def _config(**overrides) -> OptimizationConfiguration:
    base = {"strategy_id": "s1", "symbol": "EURUSD", "timeframe": "H1", "search_method": SearchMethod.GRID, "objective": Objective.NET_PROFIT}
    base.update(overrides)
    return OptimizationConfiguration(**base)


def test_grid_search_produces_full_cartesian_product() -> None:
    candidates = GridSearchOptimizer().generate(_space(), _config())
    assert len(candidates) == 3 * 2


def test_grid_search_is_deterministic_and_ordered() -> None:
    c1 = GridSearchOptimizer().generate(_space(), _config())
    c2 = GridSearchOptimizer().generate(_space(), _config())
    assert c1 == c2
    assert [c.candidate_id for c in c1] == [f"C{i:06d}" for i in range(len(c1))]


def test_grid_search_respects_max_candidates_cap() -> None:
    candidates = GridSearchOptimizer().generate(_space(), _config(max_candidates=2))
    assert len(candidates) == 2


def test_grid_search_with_empty_space_returns_one_candidate() -> None:
    candidates = GridSearchOptimizer().generate(ParameterSpace(), _config())
    assert len(candidates) == 1
    assert candidates[0].parameters_json == "{}"


def test_random_search_requires_max_candidates() -> None:
    with pytest.raises(OptimizationConfigurationError):
        RandomSearchOptimizer().generate(_space(), _config(search_method=SearchMethod.RANDOM))


def test_random_search_produces_requested_count() -> None:
    candidates = RandomSearchOptimizer().generate(_space(), _config(search_method=SearchMethod.RANDOM, max_candidates=5))
    assert len(candidates) == 5


def test_random_search_is_deterministic_given_seed() -> None:
    config = _config(search_method=SearchMethod.RANDOM, max_candidates=5, random_seed=123)
    c1 = RandomSearchOptimizer().generate(_space(), config)
    c2 = RandomSearchOptimizer().generate(_space(), config)
    assert c1 == c2


def test_random_search_differs_with_different_seed() -> None:
    c1 = RandomSearchOptimizer().generate(_space(), _config(search_method=SearchMethod.RANDOM, max_candidates=10, random_seed=1))
    c2 = RandomSearchOptimizer().generate(_space(), _config(search_method=SearchMethod.RANDOM, max_candidates=10, random_seed=2))
    assert c1 != c2
