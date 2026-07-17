"""`OptimizationCompiler`: checksum determinism and identity-field exclusion."""

from app.optimization_engine.compiler import OptimizationCompiler
from app.optimization_engine.runner import OptimizationRunner


def test_checksum_is_deterministic_across_separate_runs(optimization_context) -> None:
    result1 = OptimizationRunner().execute(optimization_context)
    result2 = OptimizationRunner().execute(optimization_context)
    assert result1.checksum == result2.checksum


def test_identity_fields_differ_even_though_checksum_matches(optimization_context) -> None:
    result1 = OptimizationRunner().execute(optimization_context)
    result2 = OptimizationRunner().execute(optimization_context)
    assert result1.result_id != result2.result_id
    assert result1.metadata.optimization_id != result2.metadata.optimization_id
    assert result1.checksum == result2.checksum


def test_compiled_result_carries_base_strategy_identity(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    assert result.metadata.strategy_id == optimization_context.base_strategy_model.metadata.id
    assert result.metadata.base_strategy_model_id == optimization_context.base_strategy_model.model_id
    assert result.metadata.base_strategy_checksum == optimization_context.base_strategy_model.checksum
