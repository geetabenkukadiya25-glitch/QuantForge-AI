"""Related-item recommendations surfaced alongside an answer.

Every recommendation is derived from items the answer's own sections
already cited, cross-referenced against other attached registries --
never a new search, never a guess. This mirrors
`app.research_engine.recommendations.RecommendationEngine`'s pure,
rule-based role.
"""

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import AssistantAnswer, RecommendationItem, SearchSourceType
from app.ai_assistant.search import SearchEngine


class RecommendationEngine:
    """Builds related-item recommendations for an already-composed `AssistantAnswer`."""

    def __init__(self, search_engine: SearchEngine | None = None) -> None:
        self._search = search_engine or SearchEngine()

    def recommend(self, context: AssistantContext, answer: AssistantAnswer) -> tuple[RecommendationItem, ...]:
        recommendations: list[RecommendationItem] = []
        seen: set[tuple[SearchSourceType, str]] = set()

        cited_strategy_ids = {
            item.item_id for section in answer.sections for item in section.items if item.source_type == SearchSourceType.STRATEGY_LIBRARY
        }
        for strategy_id in sorted(cited_strategy_ids):
            for related in self._search.related_strategy_search(context, strategy_id):
                key = (related.source_type, related.item_id)
                if key in seen:
                    continue
                seen.add(key)
                recommendations.append(
                    RecommendationItem(source_type=related.source_type, item_id=related.item_id, title=related.title, reason=f"References strategy {strategy_id!r}, cited in this answer.")
                )

        return tuple(recommendations[: context.configuration.max_results_per_section])
