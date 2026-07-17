"""`ComparisonEngine`: organizes already-computed statistics, never recomputes them."""

from app.research_engine.comparison import ComparisonEngine
from app.research_engine.models import ComparisonStatistics


def _stats(strategy_id: str, net_profit: float, win_rate: float) -> ComparisonStatistics:
    return ComparisonStatistics(strategy_id=strategy_id, net_profit=net_profit, win_rate=win_rate)


def test_compare_sorts_by_strategy_id() -> None:
    stats = (_stats("zeta", 10, 50), _stats("alpha", 20, 60))
    result = ComparisonEngine().compare(stats)
    assert [s.strategy_id for s in result] == ["alpha", "zeta"]


def test_best_by_metric_returns_highest() -> None:
    stats = (_stats("a", 10, 50), _stats("b", 50, 40))
    best = ComparisonEngine().best_by_metric(stats, "net_profit")
    assert best.strategy_id == "b"


def test_worst_by_metric_returns_lowest() -> None:
    stats = (_stats("a", 10, 50), _stats("b", 50, 40))
    worst = ComparisonEngine().worst_by_metric(stats, "net_profit")
    assert worst.strategy_id == "a"


def test_best_by_metric_treats_none_as_lowest() -> None:
    stats = (ComparisonStatistics(strategy_id="a", profit_factor=None), ComparisonStatistics(strategy_id="b", profit_factor=1.5))
    best = ComparisonEngine().best_by_metric(stats, "profit_factor")
    assert best.strategy_id == "b"


def test_worst_by_metric_treats_none_as_highest() -> None:
    stats = (ComparisonStatistics(strategy_id="a", profit_factor=None), ComparisonStatistics(strategy_id="b", profit_factor=1.5))
    worst = ComparisonEngine().worst_by_metric(stats, "profit_factor")
    assert worst.strategy_id == "b"


def test_empty_input_returns_none() -> None:
    assert ComparisonEngine().best_by_metric((), "net_profit") is None
    assert ComparisonEngine().worst_by_metric((), "net_profit") is None
