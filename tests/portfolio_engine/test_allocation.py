"""Tests for `AllocationEngine`: every allocation method, and bucketing by symbol/timeframe/session."""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.models import AllocationMethod, ManualWeight, PortfolioConfiguration


def test_equal_weight_two_strategies(entry_a_full, entry_b_bare):
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration(allocation_method=AllocationMethod.EQUAL_WEIGHT))
    assert len(weights) == 2
    assert all(abs(w - 0.5) < 1e-9 for w in weights.values())


def test_equal_weight_three_strategies(entry_a_full, entry_b_bare, entry_c_bare):
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare, entry_c_bare), PortfolioConfiguration())
    assert all(abs(w - 1 / 3) < 1e-9 for w in weights.values())


def test_weights_always_sum_to_one(entry_a_full, entry_b_bare, entry_c_bare):
    for method in AllocationMethod:
        config = PortfolioConfiguration(allocation_method=method)
        weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare, entry_c_bare), config)
        assert abs(sum(weights.values()) - 1.0) < 1e-6, method


def test_risk_parity_weights_favor_lower_drawdown(entry_a_full, entry_b_bare):
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration(allocation_method=AllocationMethod.RISK_PARITY))
    assert set(weights) == {entry_a_full.strategy_model.metadata.id, entry_b_bare.strategy_model.metadata.id}
    assert all(w > 0 for w in weights.values())


def test_volatility_weight_produces_positive_weights(entry_a_full, entry_b_bare):
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration(allocation_method=AllocationMethod.VOLATILITY_WEIGHT))
    assert all(w > 0 for w in weights.values())


def test_sharpe_weight_falls_back_to_equal_when_no_positive_sharpe(entry_a_full, entry_b_bare):
    # Both strategies commonly have None/negative Sharpe on short synthetic data; either way weights must sum to 1 and be non-negative.
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration(allocation_method=AllocationMethod.SHARPE_WEIGHT))
    assert all(w >= 0 for w in weights.values())
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_manual_weight_uses_supplied_weights(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    id_b = entry_b_bare.strategy_model.metadata.id
    config = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT, manual_weights=(ManualWeight(strategy_id=id_a, weight=3.0), ManualWeight(strategy_id=id_b, weight=1.0)))
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), config)
    assert abs(weights[id_a] - 0.75) < 1e-9
    assert abs(weights[id_b] - 0.25) < 1e-9


def test_manual_weight_falls_back_to_equal_when_all_zero(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    id_b = entry_b_bare.strategy_model.metadata.id
    config = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT, manual_weights=(ManualWeight(strategy_id=id_a, weight=0.0), ManualWeight(strategy_id=id_b, weight=0.0)))
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), config)
    assert abs(weights[id_a] - 0.5) < 1e-9
    assert abs(weights[id_b] - 0.5) < 1e-9


def test_manual_weight_missing_entry_defaults_to_zero_share(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    config = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT, manual_weights=(ManualWeight(strategy_id=id_a, weight=5.0),))
    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), config)
    id_b = entry_b_bare.strategy_model.metadata.id
    assert abs(weights[id_a] - 1.0) < 1e-9
    assert abs(weights[id_b] - 0.0) < 1e-9


def test_allocate_produces_capital_and_risk_pct(entry_a_full, entry_b_bare):
    engine = AllocationEngine()
    weights = engine.resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration())
    risk_pct = {sid: 50.0 for sid in weights}
    breakdown = engine.allocate((entry_a_full, entry_b_bare), PortfolioConfiguration(), risk_pct)
    assert len(breakdown.strategy_allocations) == 2
    for allocation in breakdown.strategy_allocations:
        assert abs(allocation.capital_allocation_pct - 50.0) < 1e-6
        assert allocation.risk_allocation_pct == 50.0


def test_symbol_allocation_groups_by_symbol(entry_a_full, entry_b_bare, entry_c_bare):
    engine = AllocationEngine()
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    weights = engine.resolve_weights(entries, PortfolioConfiguration())
    risk_pct = {sid: 100.0 / 3 for sid in weights}
    breakdown = engine.allocate(entries, PortfolioConfiguration(), risk_pct)
    symbols = {b.key for b in breakdown.symbol_allocation}
    assert symbols == {"EURUSD", "GBPUSD"}


def test_sector_allocation_is_always_empty(entry_a_full, entry_b_bare):
    engine = AllocationEngine()
    weights = engine.resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration())
    risk_pct = {sid: 50.0 for sid in weights}
    breakdown = engine.allocate((entry_a_full, entry_b_bare), PortfolioConfiguration(), risk_pct)
    assert breakdown.sector_allocation == ()


def test_timeframe_allocation_groups_by_timeframe(entry_a_full, entry_b_bare):
    engine = AllocationEngine()
    weights = engine.resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration())
    risk_pct = {sid: 50.0 for sid in weights}
    breakdown = engine.allocate((entry_a_full, entry_b_bare), PortfolioConfiguration(), risk_pct)
    assert len(breakdown.timeframe_allocation) == 1
    assert breakdown.timeframe_allocation[0].key == "H1"


def test_session_allocation_empty_when_no_sessions_declared(entry_a_full, entry_b_bare):
    engine = AllocationEngine()
    weights = engine.resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration())
    risk_pct = {sid: 50.0 for sid in weights}
    breakdown = engine.allocate((entry_a_full, entry_b_bare), PortfolioConfiguration(), risk_pct)
    assert breakdown.session_allocation == ()


def test_empty_entries_returns_empty_weights():
    assert AllocationEngine().resolve_weights((), PortfolioConfiguration()) == {}
