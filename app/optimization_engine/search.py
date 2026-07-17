"""Search methods: turn a `ParameterSpace` into an ordered set of `OptimizationCandidate`s.

Framework only, per the Phase 10 spec -- Grid Search and Random Search.
No genetic algorithm, Bayesian optimization, particle swarm, or neural
optimization. Both methods are fully deterministic: Grid Search always
enumerates in the same (definition, value) order; Random Search always
seeds its RNG from `OptimizationConfiguration.random_seed`.
"""

import itertools
import json
import random
from abc import ABC, abstractmethod

from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.models import OptimizationCandidate, OptimizationConfiguration, ParameterSpace, SearchMethod


class BaseOptimizer(ABC):
    """Common contract every search method implements."""

    name: str = "BaseOptimizer"
    search_method: SearchMethod

    @abstractmethod
    def generate(self, parameter_space: ParameterSpace, configuration: OptimizationConfiguration) -> tuple[OptimizationCandidate, ...]:
        """Generate candidates for `parameter_space`, in a deterministic order."""


class GridSearchOptimizer(BaseOptimizer):
    """Exhaustively enumerates the cartesian product of every dimension's legal values."""

    name = "GridSearchOptimizer"
    search_method = SearchMethod.GRID

    def generate(self, parameter_space: ParameterSpace, configuration: OptimizationConfiguration) -> tuple[OptimizationCandidate, ...]:
        if not parameter_space.definitions:
            return (OptimizationCandidate(candidate_id="C000000", generation_index=0, search_method=self.search_method, parameters_json="{}"),)

        names = [d.name for d in parameter_space.definitions]
        value_lists = [ParameterGenerator.values_for(d) for d in parameter_space.definitions]

        candidates: list[OptimizationCandidate] = []
        for index, combo in enumerate(itertools.product(*value_lists)):
            if configuration.max_candidates is not None and index >= configuration.max_candidates:
                break
            values = dict(zip(names, combo))
            candidates.append(
                OptimizationCandidate(
                    candidate_id=f"C{index:06d}",
                    generation_index=index,
                    search_method=self.search_method,
                    parameters_json=json.dumps(values, sort_keys=True, default=str),
                )
            )
        return tuple(candidates)


class RandomSearchOptimizer(BaseOptimizer):
    """Samples `configuration.max_candidates` independent assignments from a seeded RNG."""

    name = "RandomSearchOptimizer"
    search_method = SearchMethod.RANDOM

    def generate(self, parameter_space: ParameterSpace, configuration: OptimizationConfiguration) -> tuple[OptimizationCandidate, ...]:
        if configuration.max_candidates is None:
            raise OptimizationConfigurationError("RANDOM search requires OptimizationConfiguration.max_candidates to be set.")

        rng = random.Random(configuration.random_seed)
        candidates: list[OptimizationCandidate] = []
        for index in range(configuration.max_candidates):
            values = {d.name: ParameterGenerator.sample(d, rng) for d in parameter_space.definitions}
            candidates.append(
                OptimizationCandidate(
                    candidate_id=f"C{index:06d}",
                    generation_index=index,
                    search_method=self.search_method,
                    parameters_json=json.dumps(values, sort_keys=True, default=str),
                )
            )
        return tuple(candidates)
