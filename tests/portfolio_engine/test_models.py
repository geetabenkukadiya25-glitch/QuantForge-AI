"""Tests for portfolio_engine pydantic models: frozen/hashable, validation constraints."""

import pytest
from pydantic import ValidationError

from app.portfolio_engine.metadata import PORTFOLIO_RESULT_VERSION, PortfolioMetadata
from app.portfolio_engine.models import (
    AllocationBucket,
    AllocationMethod,
    CorrelationPair,
    ExposureEntry,
    ManualWeight,
    PortfolioAnalytics,
    PortfolioConfiguration,
    RankingCategory,
    StrategyAllocation,
)


def test_portfolio_configuration_defaults():
    config = PortfolioConfiguration()
    assert config.allocation_method == AllocationMethod.EQUAL_WEIGHT
    assert config.manual_weights == ()
    assert config.min_strategies_required == 2


def test_portfolio_configuration_is_frozen():
    config = PortfolioConfiguration()
    with pytest.raises(ValidationError):
        config.allocation_method = AllocationMethod.RISK_PARITY


def test_portfolio_configuration_is_hashable():
    config = PortfolioConfiguration()
    assert isinstance(hash(config), int)


def test_portfolio_configuration_rejects_unknown_field():
    with pytest.raises(ValidationError):
        PortfolioConfiguration(not_a_real_field=1)


def test_manual_weight_requires_non_negative_weight():
    with pytest.raises(ValidationError):
        ManualWeight(strategy_id="s1", weight=-1.0)


def test_manual_weight_valid():
    mw = ManualWeight(strategy_id="s1", weight=2.5)
    assert mw.strategy_id == "s1"
    assert mw.weight == 2.5


def test_strategy_allocation_weight_bounds():
    with pytest.raises(ValidationError):
        StrategyAllocation(strategy_id="s1", strategy_name="S1", weight=1.5, capital_allocation_pct=50, risk_allocation_pct=50)


def test_strategy_allocation_valid():
    allocation = StrategyAllocation(strategy_id="s1", strategy_name="S1", weight=0.5, capital_allocation_pct=50.0, risk_allocation_pct=40.0)
    assert allocation.weight == 0.5


def test_correlation_pair_bounds():
    with pytest.raises(ValidationError):
        CorrelationPair(strategy_id_a="a", strategy_id_b="b", correlation=1.5)


def test_correlation_pair_valid_negative():
    pair = CorrelationPair(strategy_id_a="a", strategy_id_b="b", correlation=-0.9)
    assert pair.correlation == -0.9


def test_exposure_entry_bounds():
    with pytest.raises(ValidationError):
        ExposureEntry(symbol="EURUSD", exposure_pct=150.0)


def test_allocation_bucket_defaults():
    bucket = AllocationBucket(key="EURUSD", weight_pct=50.0)
    assert bucket.strategy_ids == ()


def test_portfolio_analytics_bounds():
    with pytest.raises(ValidationError):
        PortfolioAnalytics(diversification_score=150, correlation_score=0, concentration_score=0, risk_score=0, portfolio_quality_score=0)


def test_portfolio_metadata_requires_at_least_one_strategy():
    with pytest.raises(ValidationError):
        PortfolioMetadata(portfolio_id="p1", strategy_ids=(), strategy_checksums=(), backtest_result_ids=())


def test_portfolio_metadata_default_version():
    metadata = PortfolioMetadata(portfolio_id="p1", strategy_ids=("s1",), strategy_checksums=("c1",), backtest_result_ids=("b1",))
    assert metadata.result_version == PORTFOLIO_RESULT_VERSION


def test_ranking_category_has_seven_members():
    assert len(RankingCategory) == 7
    assert {c.value for c in RankingCategory} == {
        "BEST_STRATEGY", "WORST_STRATEGY", "HIGHEST_RISK", "LOWEST_RISK",
        "MOST_STABLE", "HIGHEST_CONFIDENCE", "HIGHEST_INSTITUTIONAL_SCORE",
    }


def test_allocation_method_has_five_members():
    assert len(AllocationMethod) == 5
    assert {m.value for m in AllocationMethod} == {
        "EQUAL_WEIGHT", "RISK_PARITY", "VOLATILITY_WEIGHT", "SHARPE_WEIGHT", "MANUAL_WEIGHT",
    }
