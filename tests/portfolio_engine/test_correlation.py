"""Tests for `CorrelationEngine`: pairwise correlation matrix and symbol exposure."""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.correlation import CorrelationEngine
from app.portfolio_engine.models import PortfolioConfiguration


def test_correlate_two_strategies_produces_one_pair(entry_a_full, entry_b_bare):
    matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare))
    assert len(matrix.pairs) == 1
    pair = matrix.pairs[0]
    assert -1.0 <= pair.correlation <= 1.0


def test_correlate_three_strategies_produces_three_pairs(entry_a_full, entry_b_bare, entry_c_bare):
    matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare, entry_c_bare))
    assert len(matrix.pairs) == 3


def test_correlate_single_strategy_produces_no_pairs(entry_a_full):
    matrix = CorrelationEngine().correlate((entry_a_full,))
    assert matrix.pairs == ()
    assert matrix.average_correlation == 0.0
    assert matrix.highest_pair is None
    assert matrix.lowest_pair is None


def test_correlate_empty_produces_empty_matrix():
    matrix = CorrelationEngine().correlate(())
    assert matrix.pairs == ()


def test_self_correlation_of_identical_returns_is_one(entry_a_full):
    matrix = CorrelationEngine().correlate((entry_a_full, entry_a_full))
    assert matrix.pairs[0].correlation == 1.0


def test_average_correlation_matches_mean_of_pairs(entry_a_full, entry_b_bare, entry_c_bare):
    matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare, entry_c_bare))
    expected = round(sum(p.correlation for p in matrix.pairs) / len(matrix.pairs), 6)
    assert matrix.average_correlation == expected


def test_highest_and_lowest_pair_bracket_all_correlations(entry_a_full, entry_b_bare, entry_c_bare):
    matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare, entry_c_bare))
    for pair in matrix.pairs:
        assert pair.correlation <= matrix.highest_pair.correlation
        assert pair.correlation >= matrix.lowest_pair.correlation


def test_exposure_groups_by_symbol(entry_a_full, entry_b_bare, entry_c_bare):
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    report = CorrelationEngine().exposure(entries, weights)
    symbols = {e.symbol for e in report.entries}
    assert symbols == {"EURUSD", "GBPUSD"}


def test_exposure_pct_sums_to_one_hundred(entry_a_full, entry_b_bare, entry_c_bare):
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    report = CorrelationEngine().exposure(entries, weights)
    total = sum(e.exposure_pct for e in report.entries)
    assert abs(total - 100.0) < 1e-4
