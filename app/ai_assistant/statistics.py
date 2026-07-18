"""Deterministic "which is highest/lowest" lookups over already-computed statistics.

`AssistantStatisticsEngine` never recomputes a Sharpe ratio, a drawdown,
or any other figure -- every value it compares was already produced by
the Research Engine or Portfolio Engine and merely read here.
"""

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import SearchResultItem, SearchSourceType


def _enabled_results(registry, id_field: str):
    """Every enabled, registered result body for a Research/Portfolio-shaped registry.

    `list()` returns only metadata (no rankings/statistics), and the
    metadata's own id field is a DIFFERENT id than the internal
    `result_id` key `.load()` actually needs -- there is no public way to
    go from a `list()`-returned metadata object back to its full result
    body. Reading the registry's internal `_results` mapping (never
    mutating it) is the only way to compare full result bodies without
    modifying the registry class itself, which is out of scope for this
    phase.
    """
    enabled_ids = {getattr(m, id_field) for m in registry.list(include_disabled=False)}
    return [r for r in registry._results.values() if getattr(r.metadata, id_field) in enabled_ids]  # noqa: SLF001


class AssistantStatisticsEngine:
    """Reads already-computed statistics out of attached registries to answer ranking questions."""

    def highest_sharpe_strategy(self, context: AssistantContext) -> SearchResultItem | None:
        """The strategy with the highest already-computed Sharpe ratio across every
        registered, enabled `ResearchResult`'s rankings."""
        if context.research_registry is None:
            return None

        best_entry = None
        best_research_id = None
        for result in _enabled_results(context.research_registry, "research_id"):
            for entry in result.rankings:
                sharpe = entry.statistics.sharpe_ratio
                if sharpe is None:
                    continue
                if best_entry is None or sharpe > best_entry.statistics.sharpe_ratio or (
                    sharpe == best_entry.statistics.sharpe_ratio and entry.strategy_id < best_entry.strategy_id
                ):
                    best_entry = entry
                    best_research_id = result.metadata.research_id

        if best_entry is None:
            return None
        return SearchResultItem(
            source_type=SearchSourceType.RESEARCH,
            item_id=best_entry.strategy_id,
            title=best_entry.strategy_name,
            snippet=f"Sharpe ratio {best_entry.statistics.sharpe_ratio:.4f} (from research run {best_research_id}).",
        )

    def lowest_drawdown_portfolio(self, context: AssistantContext) -> SearchResultItem | None:
        """The portfolio with the lowest already-computed `portfolio_max_drawdown_pct`
        across every registered, enabled `PortfolioResult`."""
        if context.portfolio_registry is None:
            return None

        best_result = None
        for result in _enabled_results(context.portfolio_registry, "portfolio_id"):
            if best_result is None or result.statistics.portfolio_max_drawdown_pct < best_result.statistics.portfolio_max_drawdown_pct or (
                result.statistics.portfolio_max_drawdown_pct == best_result.statistics.portfolio_max_drawdown_pct and result.metadata.portfolio_id < best_result.metadata.portfolio_id
            ):
                best_result = result

        if best_result is None:
            return None
        return SearchResultItem(
            source_type=SearchSourceType.PORTFOLIO,
            item_id=best_result.metadata.portfolio_id,
            title=f"Portfolio {best_result.metadata.portfolio_id} ({best_result.statistics.total_strategies} strategies)",
            snippet=f"Portfolio max drawdown {best_result.statistics.portfolio_max_drawdown_pct:.4f}%.",
        )
