"""Tests for `KnowledgeLookup`."""

from app.ai_assistant.knowledge import ENGINE_GLOSSARY, KnowledgeLookup


def test_explain_known_topic():
    text = KnowledgeLookup().explain("optimization")
    assert text is not None
    assert "Optimization Engine" in text


def test_explain_unknown_topic_returns_none():
    assert KnowledgeLookup().explain("not-a-real-topic") is None


def test_explain_is_case_insensitive():
    assert KnowledgeLookup().explain("OPTIMIZATION") == KnowledgeLookup().explain("optimization")


def test_glossary_covers_every_requested_explain_topic():
    required = {"optimization", "validation", "replay", "portfolio", "extraction", "indicator", "detector", "strategy"}
    assert required.issubset(ENGINE_GLOSSARY.keys())


def test_glossary_entries_are_non_empty_strings():
    for topic, text in ENGINE_GLOSSARY.items():
        assert isinstance(text, str)
        assert len(text) > 20, topic


def test_search_entries_finds_matching_entry(knowledge_registry):
    items = KnowledgeLookup().search_entries(knowledge_registry, "moving average")
    assert any(i.item_id == "kb-sma" for i in items)


def test_search_entries_no_match_returns_empty(knowledge_registry):
    items = KnowledgeLookup().search_entries(knowledge_registry, "completely-unrelated-xyz")
    assert items == ()


def test_search_entries_none_registry_returns_empty():
    assert KnowledgeLookup().search_entries(None, "sma") == ()


def test_search_entries_empty_keyword_returns_empty(knowledge_registry):
    assert KnowledgeLookup().search_entries(knowledge_registry, "") == ()


def test_search_entries_is_sorted_by_item_id(knowledge_registry):
    items = KnowledgeLookup().search_entries(knowledge_registry, "a")  # matches both entries
    ids = [i.item_id for i in items]
    assert ids == sorted(ids)
