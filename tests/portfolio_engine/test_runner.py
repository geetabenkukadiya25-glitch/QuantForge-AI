"""Tests for `PortfolioRunner`: end-to-end orchestration."""

from app.portfolio_engine.context import PortfolioContext
from app.portfolio_engine.exceptions import PortfolioValidationError
from app.portfolio_engine.models import AllocationMethod, PortfolioConfiguration
from app.portfolio_engine.runner import PortfolioRunner, SessionStatus


def test_try_execute_succeeds_for_two_strategies(portfolio_context):
    session = PortfolioRunner().try_execute(portfolio_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_returns_result_directly(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    assert result.result_id
    assert result.statistics.total_strategies == 2


def test_execute_raises_on_invalid_context(entry_a_full):
    configuration = PortfolioConfiguration(min_strategies_required=5)
    context = PortfolioContext(entries=(entry_a_full,), configuration=configuration)
    try:
        PortfolioRunner().execute(context)
        assert False, "expected PortfolioValidationError"
    except PortfolioValidationError:
        pass


def test_try_execute_never_raises_on_invalid_context(entry_a_full):
    configuration = PortfolioConfiguration(min_strategies_required=5)
    context = PortfolioContext(entries=(entry_a_full,), configuration=configuration)
    session = PortfolioRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert session.result is None


def test_result_has_every_top_level_section(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    assert result.allocation is not None
    assert result.statistics is not None
    assert result.correlation_matrix is not None
    assert result.exposure is not None
    assert result.ranking is not None
    assert result.analytics is not None
    assert result.executive_summary is not None


def test_allocation_weights_sum_to_one(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    total_weight = sum(a.weight for a in result.allocation.strategy_allocations)
    assert abs(total_weight - 1.0) < 1e-6


def test_three_strategy_portfolio_builds_successfully(three_strategy_context):
    result = PortfolioRunner().execute(three_strategy_context)
    assert result.statistics.total_strategies == 3
    assert len(result.correlation_matrix.pairs) == 3  # C(3,2)


def test_single_strategy_portfolio_builds_with_default_configuration(single_entry_context):
    """`min_strategies_required` defaults to 2, so single_entry_context normally fails --
    lower the threshold explicitly to confirm a 1-strategy portfolio still compiles cleanly."""
    from dataclasses import replace

    relaxed = replace(single_entry_context, configuration=PortfolioConfiguration(min_strategies_required=1))
    result = PortfolioRunner().execute(relaxed)
    assert result.statistics.total_strategies == 1
    assert result.correlation_matrix.pairs == ()


def test_allocation_method_equal_weight_gives_equal_shares(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    weights = [a.weight for a in result.allocation.strategy_allocations]
    assert all(abs(w - 0.5) < 1e-6 for w in weights)


def test_manual_weight_with_no_supplied_weights_falls_back_to_equal(entry_a_full, entry_b_bare):
    configuration = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT)
    context = PortfolioContext(entries=(entry_a_full, entry_b_bare), configuration=configuration)
    session = PortfolioRunner().try_execute(context)
    assert session.is_successful
    weights = [a.weight for a in session.result.allocation.strategy_allocations]
    assert all(abs(w - 0.5) < 1e-6 for w in weights)
    assert any("manual weight" in str(w).lower() for w in session.validation.warnings)
