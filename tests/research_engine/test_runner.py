"""`ResearchRunner`: validate, statistics, compare, rank, analyze, insights, recommend, compile."""

import pytest

from app.research_engine.context import ResearchContext
from app.research_engine.exceptions import ResearchValidationError
from app.research_engine.runner import ResearchRunner, SessionStatus


def test_try_execute_succeeds_for_a_valid_context(research_context) -> None:
    session = ResearchRunner().try_execute(research_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_raises_on_invalid_context(research_configuration) -> None:
    context = ResearchContext(records=(), configuration=research_configuration)
    with pytest.raises(ResearchValidationError):
        ResearchRunner().execute(context)


def test_try_execute_never_raises_on_invalid_context(research_configuration) -> None:
    context = ResearchContext(records=(), configuration=research_configuration)
    session = ResearchRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert not session.validation.is_valid


def test_result_contains_full_ranking_and_statistics(research_context, record_a_full, record_b_bare) -> None:
    result = ResearchRunner().execute(research_context)
    assert len(result.rankings) == 2
    assert len(result.statistics) == 2
    ranked_ids = {r.strategy_id for r in result.rankings}
    assert ranked_ids == {record_a_full.strategy_model.metadata.id, record_b_bare.strategy_model.metadata.id}


def test_result_contains_analytics_insights_recommendations_and_summary(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    assert result.analytics is not None
    assert len(result.strategy_insights) == 2
    assert len(result.recommendations) > 0
    assert result.executive_summary.total_strategies_analyzed == 2


def test_ranks_are_contiguous_starting_at_one(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    ranks = sorted(r.rank for r in result.rankings)
    assert ranks == list(range(1, len(ranks) + 1))


def test_run_aliases_execute(research_context) -> None:
    result = ResearchRunner().run(research_context)
    assert result.result_id
