"""Maps a classified intent to which sources should be consulted.

`QueryPlanner` is a pure, static lookup table -- separating "what sources
does this kind of question need" (planning) from "how do I read that
source" (`search.py`/`knowledge.py`) and "how do I compose an answer"
(`reasoning.py`). No search or reasoning happens here.
"""

from app.ai_assistant.models import QueryIntent, SearchSourceType

_PLAN: dict[QueryIntent, tuple[SearchSourceType, ...]] = {
    QueryIntent.EXPLAIN_STRATEGY: (SearchSourceType.STRATEGY_LIBRARY, SearchSourceType.KNOWLEDGE_BASE),
    QueryIntent.EXPLAIN_INDICATOR: (SearchSourceType.INDICATOR, SearchSourceType.KNOWLEDGE_BASE),
    QueryIntent.EXPLAIN_DETECTOR: (SearchSourceType.SMART_MONEY, SearchSourceType.KNOWLEDGE_BASE),
    QueryIntent.COMPARE_STRATEGIES: (SearchSourceType.STRATEGY_LIBRARY, SearchSourceType.RESEARCH),
    QueryIntent.HIGHEST_SHARPE_STRATEGY: (SearchSourceType.RESEARCH,),
    QueryIntent.LOWEST_DRAWDOWN_PORTFOLIO: (SearchSourceType.PORTFOLIO,),
    QueryIntent.FIND_STRATEGIES_BY_DETECTOR: (SearchSourceType.STRATEGY_LIBRARY, SearchSourceType.SMART_MONEY),
    QueryIntent.EXPLAIN_OPTIMIZATION: (SearchSourceType.DOCUMENTATION,),
    QueryIntent.EXPLAIN_VALIDATION: (SearchSourceType.DOCUMENTATION,),
    QueryIntent.EXPLAIN_REPLAY: (SearchSourceType.DOCUMENTATION,),
    QueryIntent.EXPLAIN_PORTFOLIO_ANALYTICS: (SearchSourceType.DOCUMENTATION, SearchSourceType.PORTFOLIO),
    QueryIntent.EXPLAIN_AI_EXTRACTION: (SearchSourceType.DOCUMENTATION,),
    QueryIntent.GENERAL_SEARCH: (
        SearchSourceType.KNOWLEDGE_BASE,
        SearchSourceType.RESEARCH,
        SearchSourceType.PORTFOLIO,
        SearchSourceType.STRATEGY_LIBRARY,
        SearchSourceType.INDICATOR,
        SearchSourceType.SMART_MONEY,
        SearchSourceType.DOCUMENTATION,
    ),
}


class QueryPlanner:
    """Returns the ordered tuple of sources to consult for a given intent."""

    def plan(self, intent: QueryIntent) -> tuple[SearchSourceType, ...]:
        return _PLAN[intent]
