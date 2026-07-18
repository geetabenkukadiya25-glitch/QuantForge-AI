"""Determinism tests: repeated builds of the same context produce identical checksums."""

from app.portfolio_engine.engine import PortfolioManagementEngine
from app.portfolio_engine.models import AllocationMethod, PortfolioConfiguration
from app.portfolio_engine.runner import PortfolioRunner


def test_two_runs_of_same_context_produce_identical_checksum(portfolio_context):
    result_1 = PortfolioRunner().execute(portfolio_context)
    result_2 = PortfolioRunner().execute(portfolio_context)
    assert result_1.checksum == result_2.checksum


def test_determinism_holds_across_five_repeated_builds(portfolio_context):
    checksums = {PortfolioRunner().execute(portfolio_context).checksum for _ in range(5)}
    assert len(checksums) == 1


def test_determinism_holds_for_every_allocation_method(entry_a_full, entry_b_bare):
    for method in AllocationMethod:
        configuration = PortfolioConfiguration(allocation_method=method)
        engine = PortfolioManagementEngine()
        result_1 = engine.execute((entry_a_full, entry_b_bare), configuration)
        result_2 = engine.execute((entry_a_full, entry_b_bare), configuration)
        assert result_1.checksum == result_2.checksum, method


def test_entry_order_does_not_affect_checksum(entry_a_full, entry_b_bare):
    engine = PortfolioManagementEngine()
    configuration = PortfolioConfiguration()
    result_forward = engine.execute((entry_a_full, entry_b_bare), configuration)
    result_reversed = engine.execute((entry_b_bare, entry_a_full), configuration)
    assert result_forward.checksum == result_reversed.checksum


def test_result_id_and_built_at_differ_across_runs_despite_same_checksum(portfolio_context):
    result_1 = PortfolioRunner().execute(portfolio_context)
    result_2 = PortfolioRunner().execute(portfolio_context)
    assert result_1.result_id != result_2.result_id
    assert result_1.checksum == result_2.checksum
