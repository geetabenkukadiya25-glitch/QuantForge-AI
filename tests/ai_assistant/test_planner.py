"""Tests for `QueryPlanner`."""

from app.ai_assistant.models import QueryIntent, SearchSourceType
from app.ai_assistant.planner import QueryPlanner


def test_plan_returns_tuple_for_every_intent():
    planner = QueryPlanner()
    for intent in QueryIntent:
        plan = planner.plan(intent)
        assert isinstance(plan, tuple)
        assert len(plan) > 0


def test_explain_strategy_plan_includes_strategy_library():
    plan = QueryPlanner().plan(QueryIntent.EXPLAIN_STRATEGY)
    assert SearchSourceType.STRATEGY_LIBRARY in plan


def test_highest_sharpe_plan_is_research_only():
    plan = QueryPlanner().plan(QueryIntent.HIGHEST_SHARPE_STRATEGY)
    assert plan == (SearchSourceType.RESEARCH,)


def test_lowest_drawdown_plan_is_portfolio_only():
    plan = QueryPlanner().plan(QueryIntent.LOWEST_DRAWDOWN_PORTFOLIO)
    assert plan == (SearchSourceType.PORTFOLIO,)


def test_explain_optimization_plan_is_documentation_only():
    plan = QueryPlanner().plan(QueryIntent.EXPLAIN_OPTIMIZATION)
    assert plan == (SearchSourceType.DOCUMENTATION,)


def test_general_search_plan_covers_every_source_type():
    plan = QueryPlanner().plan(QueryIntent.GENERAL_SEARCH)
    assert set(plan) == set(SearchSourceType)


def test_plan_is_deterministic():
    planner = QueryPlanner()
    plans = {planner.plan(QueryIntent.EXPLAIN_STRATEGY) for _ in range(5)}
    assert len(plans) == 1
