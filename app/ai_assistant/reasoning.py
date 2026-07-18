"""Composes a deterministic `AssistantAnswer` from a classified intent.

`ReasoningEngine` is pure rule-based text assembly -- for each intent it
calls exactly one or two `SearchEngine`/`KnowledgeLookup`/
`AssistantStatisticsEngine` methods and formats their (already-real,
already-sourced) results into `AnswerSection`s. It never invents a fact:
if a lookup returns nothing, the section says so explicitly instead of
guessing.
"""

import re

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.knowledge import KnowledgeLookup
from app.ai_assistant.models import AnswerSection, AssistantAnswer, IntentClassification, QueryIntent, SearchSourceType
from app.ai_assistant.search import SearchEngine
from app.ai_assistant.statistics import AssistantStatisticsEngine

_STOPWORDS = {
    "explain", "this", "the", "a", "an", "what", "is", "does", "do", "of", "for", "me",
    "strategy", "indicator", "detector", "please", "show", "find", "compare", "and",
}

_EXPLAIN_TOPIC_BY_INTENT = {
    QueryIntent.EXPLAIN_OPTIMIZATION: "optimization",
    QueryIntent.EXPLAIN_VALIDATION: "validation",
    QueryIntent.EXPLAIN_REPLAY: "replay",
    QueryIntent.EXPLAIN_PORTFOLIO_ANALYTICS: "portfolio",
    QueryIntent.EXPLAIN_AI_EXTRACTION: "extraction",
    QueryIntent.EXPLAIN_INDICATOR: "indicator",
    QueryIntent.EXPLAIN_DETECTOR: "detector",
    QueryIntent.EXPLAIN_STRATEGY: "strategy",
}


def _extract_subject(query: str) -> str:
    """Strips known intent-trigger stopwords, leaving whatever specific name/id remains."""
    words = re.findall(r"[a-zA-Z0-9_\-]+", query.lower())
    remaining = [w for w in words if w not in _STOPWORDS]
    return " ".join(remaining).strip()


class ReasoningEngine:
    """Builds the full `AssistantAnswer` for one classified query."""

    def __init__(self, search_engine: SearchEngine | None = None, knowledge_lookup: KnowledgeLookup | None = None, statistics_engine: AssistantStatisticsEngine | None = None) -> None:
        self._search = search_engine or SearchEngine()
        self._knowledge = knowledge_lookup or KnowledgeLookup()
        self._statistics = statistics_engine or AssistantStatisticsEngine()

    def answer(self, context: AssistantContext, classification: IntentClassification) -> AssistantAnswer:
        intent = classification.intent
        handler = getattr(self, f"_handle_{intent.value.lower()}", self._handle_general_search)
        sections, sources_consulted = handler(context, classification)
        return AssistantAnswer(query=context.query, intent=intent, sections=sections, sources_consulted=sources_consulted)

    # -- per-intent handlers -------------------------------------------------

    def _handle_explain_strategy(self, context, classification):
        subject = _extract_subject(context.query)
        # An empty subject matches every strategy name/id (substring of everything),
        # which deliberately lists the whole Strategy Library when no name was given.
        items = self._search.registry_search(context, SearchSourceType.STRATEGY_LIBRARY, subject)
        if subject:
            body = f"Strategy Library entries matching {subject!r}." if items else f"No strategy matching {subject!r} was found in the Strategy Library."
        else:
            body = "No specific strategy was named; showing every strategy in the Strategy Library." if items else "The Strategy Library has no registered strategies."
        return (AnswerSection(heading="Strategy", body=body, items=items),), (SearchSourceType.STRATEGY_LIBRARY,)

    def _handle_explain_indicator(self, context, classification):
        subject = _extract_subject(context.query)
        description = None
        if context.indicator_registry is not None and subject:
            for metadata in context.indicator_registry.list():
                if metadata.name.lower() == subject:
                    description = metadata.description
                    break
        if description:
            section = AnswerSection(heading=f"Indicator: {subject.upper()}", body=description)
        else:
            items = self._search.registry_search(context, SearchSourceType.INDICATOR, subject)
            if subject:
                body = f"Indicators matching {subject!r}." if items else f"No indicator matching {subject!r} is registered."
            else:
                body = "No specific indicator was named; showing every registered indicator." if items else "No indicators are registered."
            section = AnswerSection(heading="Indicator", body=body, items=items)
        return (section,), (SearchSourceType.INDICATOR,)

    def _handle_explain_detector(self, context, classification):
        subject = classification.detector_hint or _extract_subject(context.query)
        description = None
        if context.smc_registry is not None and subject:
            for metadata in context.smc_registry.list():
                if metadata.name.lower() == subject.lower():
                    description = metadata.description
                    break
        if description:
            section = AnswerSection(heading=f"Detector: {subject}", body=description)
        else:
            items = self._search.registry_search(context, SearchSourceType.SMART_MONEY, subject)
            if subject:
                body = f"Detectors matching {subject!r}." if items else f"No detector matching {subject!r} is registered."
            else:
                body = "No specific detector was named; showing every registered detector." if items else "No detectors are registered."
            section = AnswerSection(heading="Detector", body=body, items=items)
        return (section,), (SearchSourceType.SMART_MONEY,)

    def _handle_compare_strategies(self, context, classification):
        parts = re.split(r"\bvs\.?\b|\bversus\b", context.query.lower())
        subjects = [_extract_subject(p) for p in parts if _extract_subject(p)]
        sections = []
        for subject in subjects[:2]:
            items = self._search.registry_search(context, SearchSourceType.STRATEGY_LIBRARY, subject)
            body = f"Strategy Library entries matching {subject!r}." if items else f"No strategy matching {subject!r} was found."
            sections.append(AnswerSection(heading=f"Candidate: {subject}", body=body, items=items))
        if len(subjects) < 2:
            sections.append(AnswerSection(heading="Comparison", body="Could not identify two distinct strategy names in the query; name both strategies explicitly (e.g. 'compare strategy-a vs strategy-b')."))
        return tuple(sections), (SearchSourceType.STRATEGY_LIBRARY, SearchSourceType.RESEARCH)

    def _handle_highest_sharpe_strategy(self, context, classification):
        best = self._statistics.highest_sharpe_strategy(context)
        if best is None:
            section = AnswerSection(heading="Highest Sharpe Strategy", body="No registered Research result carries a strategy with a computed Sharpe ratio.")
        else:
            section = AnswerSection(heading="Highest Sharpe Strategy", body=f"{best.title} has the highest recorded Sharpe ratio.", items=(best,))
        return (section,), (SearchSourceType.RESEARCH,)

    def _handle_lowest_drawdown_portfolio(self, context, classification):
        best = self._statistics.lowest_drawdown_portfolio(context)
        if best is None:
            section = AnswerSection(heading="Lowest Drawdown Portfolio", body="No registered Portfolio result is available.")
        else:
            section = AnswerSection(heading="Lowest Drawdown Portfolio", body=f"{best.title} has the lowest recorded portfolio max drawdown.", items=(best,))
        return (section,), (SearchSourceType.PORTFOLIO,)

    def _handle_find_strategies_by_detector(self, context, classification):
        detector = classification.detector_hint or _extract_subject(context.query)
        items = self._search.related_detector_search(context, detector)
        body = f"Strategies in the Strategy Library declaring a {detector} component." if items else f"No strategy in the Strategy Library declares a {detector} component."
        return (AnswerSection(heading=f"Strategies using {detector}", body=body, items=items),), (SearchSourceType.STRATEGY_LIBRARY,)

    def _handle_explain_optimization(self, context, classification):
        return self._explain_topic("optimization")

    def _handle_explain_validation(self, context, classification):
        return self._explain_topic("validation")

    def _handle_explain_replay(self, context, classification):
        return self._explain_topic("replay")

    def _handle_explain_portfolio_analytics(self, context, classification):
        sections, sources = self._explain_topic("portfolio")
        return sections, sources + (SearchSourceType.PORTFOLIO,)

    def _handle_explain_ai_extraction(self, context, classification):
        return self._explain_topic("extraction")

    def _handle_general_search(self, context, classification):
        subject = _extract_subject(context.query) or context.query.strip()
        items = self._search.keyword_search(context, subject)
        kb_items = self._knowledge.search_entries(context.knowledge_registry, subject)
        body = f"Results across every attached source for {subject!r}." if (items or kb_items) else f"No matching data found in the registered sources for {subject!r}."
        sections = (AnswerSection(heading="Search Results", body=body, items=items + kb_items),)
        return sections, (
            SearchSourceType.KNOWLEDGE_BASE, SearchSourceType.RESEARCH, SearchSourceType.PORTFOLIO,
            SearchSourceType.STRATEGY_LIBRARY, SearchSourceType.INDICATOR, SearchSourceType.SMART_MONEY,
        )

    def _explain_topic(self, topic: str):
        explanation = self._knowledge.explain(topic)
        section = AnswerSection(heading=topic.replace("_", " ").title(), body=explanation or f"No documentation entry is available for {topic!r}.")
        return (section,), (SearchSourceType.DOCUMENTATION,)
