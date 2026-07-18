"""Tests for `PortfolioContext`/`PortfolioStrategyEntry`."""

import dataclasses

import pytest

from app.portfolio_engine.context import PortfolioStrategyEntry


def test_entry_requires_only_model_and_backtest(strategy_model_b, backtest_result_b):
    entry = PortfolioStrategyEntry(strategy_model=strategy_model_b, backtest_result=backtest_result_b)
    assert entry.optimization_result is None
    assert entry.validation_result is None
    assert entry.replay_result is None
    assert entry.research_result is None


def test_entry_carries_every_optional_output(entry_a_full):
    assert entry_a_full.optimization_result is not None
    assert entry_a_full.validation_result is not None
    assert entry_a_full.replay_result is not None
    assert entry_a_full.research_result is not None


def test_entry_is_frozen(entry_b_bare):
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry_b_bare.strategy_model = None


def test_context_bundles_entries_and_configuration(portfolio_context, portfolio_configuration):
    assert len(portfolio_context.entries) == 2
    assert portfolio_context.configuration is portfolio_configuration


def test_context_is_frozen(portfolio_context):
    with pytest.raises(dataclasses.FrozenInstanceError):
        portfolio_context.entries = ()
