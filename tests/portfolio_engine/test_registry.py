"""Tests for `PortfolioRegistry`."""

import pytest

from app.portfolio_engine.exceptions import PortfolioDisabledError, PortfolioNotFoundError, PortfolioRegistrationError
from app.portfolio_engine.registry import PortfolioRegistry
from app.portfolio_engine.runner import PortfolioRunner


@pytest.fixture
def portfolio_result(portfolio_context):
    return PortfolioRunner().execute(portfolio_context)


def test_register_and_load(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    assert registry.load(portfolio_result.result_id) is portfolio_result


def test_register_duplicate_raises(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    with pytest.raises(PortfolioRegistrationError):
        registry.register(portfolio_result)


def test_register_duplicate_with_overwrite_succeeds(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    registry.register(portfolio_result, overwrite=True)  # should not raise


def test_load_unknown_raises(portfolio_result):
    registry = PortfolioRegistry()
    with pytest.raises(PortfolioNotFoundError):
        registry.load("unknown-id")


def test_is_registered(portfolio_result):
    registry = PortfolioRegistry()
    assert not registry.is_registered(portfolio_result.result_id)
    registry.register(portfolio_result)
    assert registry.is_registered(portfolio_result.result_id)


def test_enabled_by_default(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    assert registry.is_enabled(portfolio_result.result_id)


def test_disable_and_require_enabled_raises(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    registry.disable(portfolio_result.result_id)
    assert not registry.is_enabled(portfolio_result.result_id)
    with pytest.raises(PortfolioDisabledError):
        registry.require_enabled(portfolio_result.result_id)


def test_re_enable(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    registry.disable(portfolio_result.result_id)
    registry.enable(portfolio_result.result_id)
    assert registry.is_enabled(portfolio_result.result_id)


def test_list_sorted_by_id(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    listed = registry.list()
    assert listed == sorted(listed, key=lambda m: m.portfolio_id)


def test_search_by_strategy_id(portfolio_result):
    registry = PortfolioRegistry()
    registry.register(portfolio_result)
    strategy_id = portfolio_result.metadata.strategy_ids[0]
    found = registry.search(strategy_id=strategy_id)
    assert len(found) == 1

    not_found = registry.search(strategy_id="nonexistent-strategy")
    assert not_found == []
