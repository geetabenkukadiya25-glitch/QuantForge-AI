"""Tests for app.ea_generator.compiler."""

from app.ea_generator.compiler import EACompiler
from app.ea_generator.generator import EAGenerator
from app.ea_generator.statistics import EAGeneratorStatisticsEngine


def _compile(context):
    artifacts = EAGenerator().generate(context)
    statistics = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    return EACompiler().compile(
        context,
        source_code=artifacts.source_code,
        inputs=artifacts.inputs,
        indicator_declarations=artifacts.indicator_declarations,
        risk_parameters=artifacts.risk_parameters,
        trade_management=artifacts.trade_management,
        statistics=statistics,
    )


def test_compile_produces_nonempty_checksum(ea_context) -> None:
    result = _compile(ea_context)
    assert len(result.checksum) == 64  # sha256 hex digest length


def test_compile_sets_metadata_identity(ea_context) -> None:
    result = _compile(ea_context)
    assert result.metadata.strategy_id == ea_context.strategy_model.metadata.id
    assert result.metadata.strategy_checksum == ea_context.strategy_model.checksum
    assert result.metadata.output_filename == ea_context.configuration.output_filename


def test_compile_generates_unique_result_ids(ea_context) -> None:
    first = _compile(ea_context)
    second = _compile(ea_context)
    assert first.result_id != second.result_id


def test_compile_generates_unique_ea_ids(ea_context) -> None:
    first = _compile(ea_context)
    second = _compile(ea_context)
    assert first.metadata.ea_id != second.metadata.ea_id


def test_compile_checksum_is_deterministic(ea_context) -> None:
    first = _compile(ea_context)
    second = _compile(ea_context)
    assert first.checksum == second.checksum


def test_compile_checksum_changes_with_configuration(strategy_model_a):
    from app.ea_generator.context import EAGeneratorContext
    from app.ea_generator.models import EAGeneratorConfiguration

    context_a = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(magic_number=1))
    context_b = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(magic_number=2))
    result_a = _compile(context_a)
    result_b = _compile(context_b)
    assert result_a.checksum != result_b.checksum


def test_compile_carries_source_code_through(ea_context) -> None:
    result = _compile(ea_context)
    assert result.source_code
    assert ea_context.strategy_model.metadata.id in result.source_code
