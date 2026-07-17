"""Reconstructs the exact `StrategyModel`/`BacktestConfiguration` an Optimization
Engine candidate represents -- WITHOUT re-running the Optimization Engine.

This is the module's core "consume Optimization Engine outputs, never
optimize" boundary: `resolve_candidate()` reads one already-produced
`OptimizationCandidateOutcome` and deterministically rebuilds the exact
artifacts it represents using `app.optimization_engine.generator.ParameterGenerator`
(the same pure derivation Optimization Engine itself used) -- it never
searches, scores, or compares candidates. A checksum match against the
outcome's own recorded `strategy_checksum` is verified defensively before
any candidate is used.
"""

import json
from dataclasses import dataclass

from app.backtesting_engine.models import BacktestConfiguration
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.models import OptimizationCandidateOutcome
from app.strategy_builder.models import StrategyModel
from app.validation_engine.context import ValidationContext
from app.validation_engine.exceptions import ValidationConfigurationError, ValidationExecutionError


@dataclass(frozen=True)
class ResolvedCandidate:
    """The reconstructed, ready-to-backtest artifacts for one chosen Optimization Engine candidate."""

    strategy_model: StrategyModel
    configuration: BacktestConfiguration
    outcome: OptimizationCandidateOutcome


def resolve_candidate(context: ValidationContext) -> ResolvedCandidate:
    """Resolve `context.candidate_id` (or the optimization result's best candidate) into concrete artifacts.

    Raises:
        ValidationConfigurationError: if no candidate id is available, or
            the referenced candidate doesn't exist or didn't succeed.
        ValidationExecutionError: if the reconstructed StrategyModel's
            checksum doesn't match the Optimization Engine's own record
            (defensive -- should never happen given deterministic derivation).
    """
    candidate_id = context.candidate_id or context.optimization_result.best_candidate_id
    if candidate_id is None:
        raise ValidationConfigurationError("No candidate_id given and the OptimizationResult has no best_candidate_id.")

    outcome = next((e for e in context.optimization_result.history.entries if e.candidate_id == candidate_id), None)
    if outcome is None:
        raise ValidationConfigurationError(f"Candidate {candidate_id!r} not found in the OptimizationResult's history.")
    if not outcome.succeeded:
        raise ValidationConfigurationError(f"Candidate {candidate_id!r} did not succeed during optimization; nothing to validate.")

    values = json.loads(outcome.parameters_json)
    strategy_model = ParameterGenerator.apply_to_model(context.base_strategy_model, values)
    configuration = ParameterGenerator.apply_to_configuration(context.base_configuration, values)

    if strategy_model.checksum != outcome.strategy_checksum:
        raise ValidationExecutionError(
            f"Reconstructed StrategyModel checksum {strategy_model.checksum!r} does not match "
            f"the Optimization Engine's recorded checksum {outcome.strategy_checksum!r} for candidate {candidate_id!r}."
        )

    return ResolvedCandidate(strategy_model=strategy_model, configuration=configuration, outcome=outcome)
