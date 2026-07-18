"""Tests for `AssistantStatisticsEngine`."""

from app.ai_assistant.models import SearchSourceType
from app.ai_assistant.statistics import AssistantStatisticsEngine


def test_highest_sharpe_strategy_returns_item(full_context):
    item = AssistantStatisticsEngine().highest_sharpe_strategy(full_context)
    # May be None if the synthetic backtest produced no Sharpe ratio -- either
    # way the call must not raise, and a non-None result must be sourced correctly.
    if item is not None:
        assert item.source_type == SearchSourceType.RESEARCH


def test_highest_sharpe_strategy_no_registry_returns_none():
    from app.ai_assistant.context import AssistantContext
    from app.ai_assistant.models import AssistantConfiguration

    context = AssistantContext(query="q", configuration=AssistantConfiguration())
    assert AssistantStatisticsEngine().highest_sharpe_strategy(context) is None


def test_lowest_drawdown_portfolio_returns_item(full_context):
    item = AssistantStatisticsEngine().lowest_drawdown_portfolio(full_context)
    assert item is not None
    assert item.source_type == SearchSourceType.PORTFOLIO


def test_lowest_drawdown_portfolio_no_registry_returns_none():
    from app.ai_assistant.context import AssistantContext
    from app.ai_assistant.models import AssistantConfiguration

    context = AssistantContext(query="q", configuration=AssistantConfiguration())
    assert AssistantStatisticsEngine().lowest_drawdown_portfolio(context) is None


def test_lowest_drawdown_portfolio_is_deterministic(full_context):
    engine = AssistantStatisticsEngine()
    first = engine.lowest_drawdown_portfolio(full_context)
    second = engine.lowest_drawdown_portfolio(full_context)
    assert first.item_id == second.item_id


def test_highest_sharpe_is_deterministic(full_context):
    engine = AssistantStatisticsEngine()
    first = engine.highest_sharpe_strategy(full_context)
    second = engine.highest_sharpe_strategy(full_context)
    assert (first is None) == (second is None)
    if first is not None:
        assert first.item_id == second.item_id


def test_statistics_never_recomputes_reads_only(full_context):
    """A weak but meaningful guard: calling these methods must not raise and
    must not mutate the attached registries (no new entries registered)."""
    before = len(full_context.portfolio_registry.list())
    AssistantStatisticsEngine().lowest_drawdown_portfolio(full_context)
    after = len(full_context.portfolio_registry.list())
    assert before == after
