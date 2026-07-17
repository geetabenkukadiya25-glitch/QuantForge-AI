"""`resolve_candidate`: reconstructing an Optimization Engine candidate WITHOUT re-optimizing."""

import dataclasses

import pytest

from app.validation_engine.exceptions import ValidationConfigurationError
from app.validation_engine.resolve import resolve_candidate


def test_resolves_best_candidate_by_default(validation_context) -> None:
    resolved = resolve_candidate(validation_context)
    assert resolved.outcome.candidate_id == validation_context.optimization_result.best_candidate_id
    assert resolved.strategy_model.checksum == resolved.outcome.strategy_checksum


def test_resolves_explicit_candidate_id(validation_context) -> None:
    other_id = next(e.candidate_id for e in validation_context.optimization_result.history.entries if e.succeeded)
    context = dataclasses.replace(validation_context, candidate_id=other_id)
    resolved = resolve_candidate(context)
    assert resolved.outcome.candidate_id == other_id


def test_unknown_candidate_id_raises(validation_context) -> None:
    context = dataclasses.replace(validation_context, candidate_id="nonexistent")
    with pytest.raises(ValidationConfigurationError):
        resolve_candidate(context)


def test_reconstructed_model_matches_base_when_no_overrides(validation_context) -> None:
    resolved = resolve_candidate(validation_context)
    # The resolved candidate's model is a derived copy -- same content
    # family as the base model (same rules/context_requirement), never a
    # re-invocation of Strategy Builder.
    assert resolved.strategy_model.metadata.id == validation_context.base_strategy_model.metadata.id
