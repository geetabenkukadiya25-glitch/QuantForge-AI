"""Deterministic search over every attached, already-built registry.

No embeddings, no vector database, no external AI -- every method here
is a plain keyword/substring/tag filter over data an attached registry
already holds. `SearchEngine` never mutates a registry and never invokes
another engine's runner/compiler; it only reads `list()`/`search()`/
`load()` results each registry already exposes.
"""

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import SearchResultItem, SearchSourceType


def _enabled_research_results(registry) -> list:
    """Every enabled, registered `ResearchResult` body.

    `ResearchRegistry.list()` returns only `ResearchMetadata` (no
    rankings/analytics), and `ResearchMetadata.research_id` is a
    DIFFERENT id than the internal `result_id` key `.load()` actually
    needs -- there is no public way to go from a `list()`-returned
    metadata object back to its full result body. Reading the registry's
    internal `_results` mapping (never mutating it) is the only way to
    search full result bodies without modifying `ResearchRegistry`
    itself, which is out of scope for this phase.
    """
    enabled_ids = {m.research_id for m in registry.list(include_disabled=False)}
    return [r for r in registry._results.values() if r.metadata.research_id in enabled_ids]  # noqa: SLF001


def _enabled_portfolio_results(registry) -> list:
    """Every enabled, registered `PortfolioResult` body -- see `_enabled_research_results`
    for why the internal `_results` mapping must be read directly."""
    enabled_ids = {m.portfolio_id for m in registry.list(include_disabled=False)}
    return [r for r in registry._results.values() if r.metadata.portfolio_id in enabled_ids]  # noqa: SLF001


class SearchEngine:
    """Keyword/tag/category/registry search across every source an `AssistantContext` carries."""

    def keyword_search(self, context: AssistantContext, keyword: str) -> tuple[SearchResultItem, ...]:
        """Search every attached source for `keyword`, merged and sorted for determinism."""
        if not keyword or len(keyword) < context.configuration.min_keyword_length:
            return ()
        items: list[SearchResultItem] = []
        items.extend(self._search_strategy_library(context, keyword))
        items.extend(self._search_indicators(context, keyword))
        items.extend(self._search_detectors(context, keyword))
        items.extend(self._search_research(context, keyword))
        items.extend(self._search_portfolio(context, keyword))
        return self._cap(self._sorted(items), context)

    def tag_search(self, context: AssistantContext, tag: str) -> tuple[SearchResultItem, ...]:
        """Strategies in the Strategy Library carrying `tag`."""
        if context.strategy_registry is None or not tag:
            return ()
        needle = tag.strip().lower()
        items = [
            SearchResultItem(source_type=SearchSourceType.STRATEGY_LIBRARY, item_id=s.id, title=s.name, tags=tuple(s.tags))
            for s in context.strategy_registry.list()
            if needle in {t.lower() for t in s.tags}
        ]
        return self._cap(self._sorted(items), context)

    def category_search(self, context: AssistantContext, category: str) -> tuple[SearchResultItem, ...]:
        """Indicators and detectors registered under `category`."""
        items: list[SearchResultItem] = []
        if context.indicator_registry is not None:
            items.extend(
                SearchResultItem(source_type=SearchSourceType.INDICATOR, item_id=m.name, title=m.name, snippet=m.description, tags=(m.category,))
                for m in context.indicator_registry.search(category=category)
            )
        if context.smc_registry is not None:
            items.extend(
                SearchResultItem(source_type=SearchSourceType.SMART_MONEY, item_id=m.name, title=m.name, snippet=m.description, tags=(m.category,))
                for m in context.smc_registry.search(category=category)
            )
        return self._cap(self._sorted(items), context)

    def registry_search(self, context: AssistantContext, source_type: SearchSourceType, keyword: str) -> tuple[SearchResultItem, ...]:
        """Search exactly one named source for `keyword`."""
        dispatch = {
            SearchSourceType.STRATEGY_LIBRARY: self._search_strategy_library,
            SearchSourceType.INDICATOR: self._search_indicators,
            SearchSourceType.SMART_MONEY: self._search_detectors,
            SearchSourceType.RESEARCH: self._search_research,
            SearchSourceType.PORTFOLIO: self._search_portfolio,
        }
        handler = dispatch.get(source_type)
        if handler is None:
            return ()
        return self._cap(self._sorted(list(handler(context, keyword))), context)

    def related_strategy_search(self, context: AssistantContext, strategy_id: str) -> tuple[SearchResultItem, ...]:
        """Research/Portfolio results that also analyzed `strategy_id`."""
        items: list[SearchResultItem] = []
        if context.research_registry is not None:
            for metadata in context.research_registry.list(include_disabled=False):
                if strategy_id in metadata.strategy_ids:
                    items.append(SearchResultItem(source_type=SearchSourceType.RESEARCH, item_id=metadata.research_id, title=f"Research run analyzing {strategy_id}"))
        if context.portfolio_registry is not None:
            for metadata in context.portfolio_registry.list(include_disabled=False):
                if strategy_id in metadata.strategy_ids:
                    items.append(SearchResultItem(source_type=SearchSourceType.PORTFOLIO, item_id=metadata.portfolio_id, title=f"Portfolio containing {strategy_id}"))
        return self._cap(self._sorted(items), context)

    def related_indicator_search(self, context: AssistantContext, indicator_type: str) -> tuple[SearchResultItem, ...]:
        """Strategies in the Strategy Library that declare an indicator of `indicator_type`."""
        return self._strategies_using_component(context, indicator_type)

    def related_detector_search(self, context: AssistantContext, detector_type: str) -> tuple[SearchResultItem, ...]:
        """Strategies in the Strategy Library that declare a detector of `detector_type`

        (SDL stores indicator AND detector references in the same generic
        `indicators:` list -- see `app.sdl.models.StrategyDefinition.indicators`)."""
        return self._strategies_using_component(context, detector_type)

    def _strategies_using_component(self, context: AssistantContext, component_type: str) -> tuple[SearchResultItem, ...]:
        if context.strategy_registry is None or not component_type:
            return ()
        needle = component_type.strip().lower()
        items: list[SearchResultItem] = []
        for summary in context.strategy_registry.list():
            try:
                definition = context.strategy_registry.load(summary.id)
            except Exception:  # a corrupt/unreadable strategy file shouldn't break the search
                continue
            if any(spec.type.lower() == needle for spec in definition.indicators):
                items.append(SearchResultItem(source_type=SearchSourceType.STRATEGY_LIBRARY, item_id=summary.id, title=summary.name, tags=tuple(summary.tags)))
        return self._cap(self._sorted(items), context)

    # -- per-source keyword search -----------------------------------------

    @staticmethod
    def _search_strategy_library(context: AssistantContext, keyword: str) -> list[SearchResultItem]:
        if context.strategy_registry is None:
            return []
        needle = keyword.lower()
        return [
            SearchResultItem(source_type=SearchSourceType.STRATEGY_LIBRARY, item_id=s.id, title=s.name, tags=tuple(s.tags))
            for s in context.strategy_registry.search(query=keyword)
            if needle in s.name.lower() or needle in s.id.lower()
        ]

    @staticmethod
    def _search_indicators(context: AssistantContext, keyword: str) -> list[SearchResultItem]:
        if context.indicator_registry is None:
            return []
        needle = keyword.lower()
        return [
            SearchResultItem(source_type=SearchSourceType.INDICATOR, item_id=m.name, title=m.name, snippet=m.description, tags=(m.category,))
            for m in context.indicator_registry.list()
            if needle in m.name.lower() or needle in m.description.lower()
        ]

    @staticmethod
    def _search_detectors(context: AssistantContext, keyword: str) -> list[SearchResultItem]:
        if context.smc_registry is None:
            return []
        needle = keyword.lower()
        return [
            SearchResultItem(source_type=SearchSourceType.SMART_MONEY, item_id=m.name, title=m.name, snippet=m.description, tags=(m.category,))
            for m in context.smc_registry.list()
            if needle in m.name.lower() or needle in m.description.lower()
        ]

    @staticmethod
    def _search_research(context: AssistantContext, keyword: str) -> list[SearchResultItem]:
        if context.research_registry is None:
            return []
        needle = keyword.lower()
        items = []
        for result in _enabled_research_results(context.research_registry):
            for ranking_entry in result.rankings:
                if needle in ranking_entry.strategy_name.lower() or needle in ranking_entry.strategy_id.lower():
                    items.append(SearchResultItem(source_type=SearchSourceType.RESEARCH, item_id=result.metadata.research_id, title=f"Research run ranking {ranking_entry.strategy_name}"))
        return items

    @staticmethod
    def _search_portfolio(context: AssistantContext, keyword: str) -> list[SearchResultItem]:
        if context.portfolio_registry is None:
            return []
        needle = keyword.lower()
        items = []
        for result in _enabled_portfolio_results(context.portfolio_registry):
            for allocation in result.allocation.strategy_allocations:
                if needle in allocation.strategy_name.lower() or needle in allocation.strategy_id.lower():
                    items.append(SearchResultItem(source_type=SearchSourceType.PORTFOLIO, item_id=result.metadata.portfolio_id, title=f"Portfolio containing {allocation.strategy_name}"))
        return items

    @staticmethod
    def _sorted(items: list[SearchResultItem]) -> list[SearchResultItem]:
        return sorted(items, key=lambda i: (i.source_type.value, i.item_id))

    @staticmethod
    def _cap(items: list[SearchResultItem], context: AssistantContext) -> tuple[SearchResultItem, ...]:
        return tuple(items[: context.configuration.max_results_per_section])
