"""`ValidationCompiler`: checksum determinism and identity-field exclusion."""

from app.validation_engine.runner import ValidationRunner


def test_checksum_is_deterministic_across_separate_runs(validation_context) -> None:
    result1 = ValidationRunner().execute(validation_context)
    result2 = ValidationRunner().execute(validation_context)
    assert result1.checksum == result2.checksum


def test_identity_fields_differ_even_though_checksum_matches(validation_context) -> None:
    result1 = ValidationRunner().execute(validation_context)
    result2 = ValidationRunner().execute(validation_context)
    assert result1.result_id != result2.result_id
    assert result1.metadata.validation_id != result2.metadata.validation_id
    assert result1.checksum == result2.checksum


def test_compiled_result_carries_optimization_and_candidate_identity(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    assert result.metadata.optimization_result_id == validation_context.optimization_result.result_id
    assert result.metadata.optimization_checksum == validation_context.optimization_result.checksum
    assert result.metadata.candidate_id == (validation_context.candidate_id or validation_context.optimization_result.best_candidate_id)
