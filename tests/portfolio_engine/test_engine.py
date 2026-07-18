"""Tests for `PortfolioManagementEngine`: the top-level facade."""

import pytest

from app.portfolio_engine.engine import PortfolioManagementEngine
from app.portfolio_engine.exceptions import PortfolioValidationError
from app.portfolio_engine.models import PortfolioConfiguration


def test_execute_returns_portfolio_result(entry_a_full, entry_b_bare):
    engine = PortfolioManagementEngine()
    result = engine.execute((entry_a_full, entry_b_bare), PortfolioConfiguration())
    assert result.statistics.total_strategies == 2


def test_try_execute_never_raises(entry_a_full):
    engine = PortfolioManagementEngine()
    session = engine.try_execute((entry_a_full,), PortfolioConfiguration(min_strategies_required=5))
    assert not session.is_successful


def test_execute_raises_on_invalid_input(entry_a_full):
    engine = PortfolioManagementEngine()
    with pytest.raises(PortfolioValidationError):
        engine.execute((entry_a_full,), PortfolioConfiguration(min_strategies_required=5))


def test_run_aliases_execute(entry_a_full, entry_b_bare):
    engine = PortfolioManagementEngine()
    result_via_run = engine.run((entry_a_full, entry_b_bare), PortfolioConfiguration())
    assert result_via_run.statistics.total_strategies == 2


def test_engine_name_is_set():
    assert PortfolioManagementEngine.name == "PortfolioManagementEngine"


def test_engine_accepts_injected_runner(entry_a_full, entry_b_bare):
    from app.portfolio_engine.runner import PortfolioRunner

    custom_runner = PortfolioRunner()
    engine = PortfolioManagementEngine(runner=custom_runner)
    result = engine.execute((entry_a_full, entry_b_bare), PortfolioConfiguration())
    assert result is not None
