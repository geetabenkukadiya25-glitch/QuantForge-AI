"""Tests for `RankingEngine`."""

from app.portfolio_engine.models import RankingCategory
from app.portfolio_engine.ranking import RankingEngine


def test_rank_always_includes_best_and_worst_strategy(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.BEST_STRATEGY in categories
    assert RankingCategory.WORST_STRATEGY in categories


def test_rank_always_includes_highest_and_lowest_risk(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.HIGHEST_RISK in categories
    assert RankingCategory.LOWEST_RISK in categories


def test_rank_includes_most_stable_when_validation_present(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.MOST_STABLE in categories


def test_rank_includes_highest_confidence_when_validation_present(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.HIGHEST_CONFIDENCE in categories


def test_rank_includes_institutional_score_when_research_present(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.HIGHEST_INSTITUTIONAL_SCORE in categories


def test_rank_omits_optional_categories_when_no_entry_has_them(entry_b_bare, entry_c_bare):
    ranking = RankingEngine().rank((entry_b_bare, entry_c_bare))
    categories = {h.category for h in ranking.highlights}
    assert RankingCategory.MOST_STABLE not in categories
    assert RankingCategory.HIGHEST_CONFIDENCE not in categories
    assert RankingCategory.HIGHEST_INSTITUTIONAL_SCORE not in categories
    assert RankingCategory.BEST_STRATEGY in categories


def test_full_order_contains_every_strategy_id_once(entry_a_full, entry_b_bare, entry_c_bare):
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    ranking = RankingEngine().rank(entries)
    expected_ids = {e.strategy_model.metadata.id for e in entries}
    assert set(ranking.full_order) == expected_ids
    assert len(ranking.full_order) == len(entries)


def test_full_order_is_sorted_best_to_worst_by_net_profit(entry_a_full, entry_b_bare, entry_c_bare):
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    ranking = RankingEngine().rank(entries)
    net_profits_by_id = {e.strategy_model.metadata.id: e.backtest_result.statistics.net_profit for e in entries}
    ordered_profits = [net_profits_by_id[sid] for sid in ranking.full_order]
    assert ordered_profits == sorted(ordered_profits, reverse=True)


def test_rank_empty_entries_returns_empty_ranking():
    ranking = RankingEngine().rank(())
    assert ranking.highlights == ()
    assert ranking.full_order == ()


def test_best_strategy_value_matches_its_net_profit(entry_a_full, entry_b_bare):
    ranking = RankingEngine().rank((entry_a_full, entry_b_bare))
    best = next(h for h in ranking.highlights if h.category == RankingCategory.BEST_STRATEGY)
    entries_by_id = {entry_a_full.strategy_model.metadata.id: entry_a_full, entry_b_bare.strategy_model.metadata.id: entry_b_bare}
    expected = round(entries_by_id[best.strategy_id].backtest_result.statistics.net_profit, 4)
    assert best.value == expected
