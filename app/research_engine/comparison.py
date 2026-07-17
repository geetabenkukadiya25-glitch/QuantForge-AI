"""Cross-strategy comparison over already-computed `ComparisonStatistics`.

`ComparisonEngine` never recomputes a statistic itself -- it only
organizes and cross-references the per-strategy `ComparisonStatistics`
`ResearchStatisticsEngine` already produced.
"""

from app.research_engine.models import ComparisonStatistics


class ComparisonEngine:
    """Organizes per-strategy statistics into a deterministic comparison table."""

    def compare(self, statistics: tuple[ComparisonStatistics, ...]) -> tuple[ComparisonStatistics, ...]:
        """Return `statistics` sorted by `strategy_id`, for a deterministic comparison table."""
        return tuple(sorted(statistics, key=lambda s: s.strategy_id))

    def best_by_metric(self, statistics: tuple[ComparisonStatistics, ...], metric: str) -> ComparisonStatistics | None:
        """Return whichever `ComparisonStatistics` has the highest value for `metric` (a field name).

        `None`/missing values are treated as the lowest possible value, so
        they never win a comparison. Returns `None` for an empty input.
        """
        if not statistics:
            return None
        return max(statistics, key=lambda s: (getattr(s, metric) if getattr(s, metric) is not None else float("-inf")))

    def worst_by_metric(self, statistics: tuple[ComparisonStatistics, ...], metric: str) -> ComparisonStatistics | None:
        """The mirror of `best_by_metric`: whichever strategy has the lowest value for `metric`."""
        if not statistics:
            return None
        return min(statistics, key=lambda s: (getattr(s, metric) if getattr(s, metric) is not None else float("inf")))
