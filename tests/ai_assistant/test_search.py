"""Tests for `SearchEngine`."""

from app.ai_assistant.models import SearchSourceType
from app.ai_assistant.search import SearchEngine
from tests.ai_assistant.conftest import make_context


def test_keyword_search_finds_strategy(full_context):
    context = make_context(full_context, "alpha")
    items = SearchEngine().keyword_search(context, "alpha")
    assert any(i.item_id == "strategy-alpha" for i in items)


def test_keyword_search_finds_indicator(full_context):
    items = SearchEngine().keyword_search(full_context, "moving average")
    assert any(i.source_type == SearchSourceType.INDICATOR for i in items)


def test_keyword_search_too_short_returns_empty(full_context):
    assert SearchEngine().keyword_search(full_context, "a") == ()  # below min_keyword_length=2


def test_keyword_search_no_match_returns_empty(full_context):
    assert SearchEngine().keyword_search(full_context, "zzz-nonexistent-zzz") == ()


def test_keyword_search_results_are_capped(full_context):
    from dataclasses import replace

    from app.ai_assistant.models import AssistantConfiguration

    tight_context = replace(full_context, configuration=AssistantConfiguration(max_results_per_section=1))
    items = SearchEngine().keyword_search(tight_context, "strategy")
    assert len(items) <= 1


def test_tag_search_finds_strategy_by_tag(full_context):
    items = SearchEngine().tag_search(full_context, "smc")
    ids = {i.item_id for i in items}
    assert "strategy-alpha" in ids
    assert "strategy-beta" in ids
    assert "strategy-gamma" not in ids


def test_tag_search_no_registry_returns_empty():
    from app.ai_assistant.context import AssistantContext
    from app.ai_assistant.models import AssistantConfiguration

    context = AssistantContext(query="q", configuration=AssistantConfiguration())
    assert SearchEngine().tag_search(context, "smc") == ()


def test_category_search_finds_indicators(full_context):
    items = SearchEngine().category_search(full_context, "Trend")
    assert len(items) > 0
    assert all(i.source_type in (SearchSourceType.INDICATOR, SearchSourceType.SMART_MONEY) for i in items)


def test_registry_search_dispatches_to_strategy_library(full_context):
    items = SearchEngine().registry_search(full_context, SearchSourceType.STRATEGY_LIBRARY, "beta")
    assert any(i.item_id == "strategy-beta" for i in items)


def test_registry_search_unknown_source_returns_empty(full_context):
    assert SearchEngine().registry_search(full_context, SearchSourceType.DOCUMENTATION, "anything") == ()


def test_related_strategy_search_finds_research_and_portfolio(full_context, strategy_model_a):
    strategy_id = strategy_model_a.metadata.id
    items = SearchEngine().related_strategy_search(full_context, strategy_id)
    source_types = {i.source_type for i in items}
    assert SearchSourceType.RESEARCH in source_types or SearchSourceType.PORTFOLIO in source_types


def test_related_strategy_search_unknown_id_returns_empty(full_context):
    assert SearchEngine().related_strategy_search(full_context, "no-such-strategy") == ()


def test_related_indicator_search_finds_strategies_using_sma(full_context):
    items = SearchEngine().related_indicator_search(full_context, "SMA")
    ids = {i.item_id for i in items}
    assert "strategy-alpha" in ids
    assert "strategy-gamma" in ids
    assert "strategy-beta" not in ids


def test_related_detector_search_finds_strategies_using_bos(full_context):
    items = SearchEngine().related_detector_search(full_context, "Break Of Structure")
    ids = {i.item_id for i in items}
    assert ids == {"strategy-alpha"}


def test_related_detector_search_finds_strategies_using_fvg(full_context):
    items = SearchEngine().related_detector_search(full_context, "Fair Value Gap")
    ids = {i.item_id for i in items}
    assert ids == {"strategy-beta"}


def test_related_detector_search_no_registry_returns_empty():
    from app.ai_assistant.context import AssistantContext
    from app.ai_assistant.models import AssistantConfiguration

    context = AssistantContext(query="q", configuration=AssistantConfiguration())
    assert SearchEngine().related_detector_search(context, "Break Of Structure") == ()


def test_keyword_search_merges_across_sources_sorted(full_context):
    items = SearchEngine().keyword_search(full_context, "strategy")
    keys = [(i.source_type.value, i.item_id) for i in items]
    assert keys == sorted(keys)
