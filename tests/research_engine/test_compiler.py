"""`ResearchCompiler`: deterministic checksum excludes identity/timestamp fields."""

from app.research_engine.compiler import ResearchCompiler
from app.research_engine.runner import ResearchRunner


def test_compile_produces_a_valid_result(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    assert result.checksum
    assert result.result_id
    assert len(result.metadata.strategy_ids) == 2


def test_same_context_produces_the_same_checksum(research_context) -> None:
    result1 = ResearchRunner().execute(research_context)
    result2 = ResearchRunner().execute(research_context)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.research_id != result2.metadata.research_id


def test_different_configuration_produces_a_different_checksum(research_context, record_a_full, record_b_bare) -> None:
    from app.research_engine.context import ResearchContext
    from app.research_engine.models import RankingMetric, ResearchConfiguration

    context_a = ResearchContext(records=(record_a_full, record_b_bare), configuration=ResearchConfiguration())
    context_b = ResearchContext(records=(record_a_full, record_b_bare), configuration=ResearchConfiguration(ranking_metric=RankingMetric.NET_PROFIT))

    result_a = ResearchRunner().execute(context_a)
    result_b = ResearchRunner().execute(context_b)
    assert result_a.checksum != result_b.checksum


def test_metadata_carries_every_strategy_and_backtest_identity(research_context, record_a_full, record_b_bare) -> None:
    result = ResearchRunner().execute(research_context)
    assert set(result.metadata.strategy_ids) == {record_a_full.strategy_model.metadata.id, record_b_bare.strategy_model.metadata.id}
    assert record_a_full.strategy_model.checksum in result.metadata.strategy_checksums
    assert record_a_full.backtest_result.result_id in result.metadata.backtest_result_ids
