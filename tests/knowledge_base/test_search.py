"""`KnowledgeSearchEngine`: category/keyword/tag/difficulty/asset/timeframe/session search."""

from app.knowledge_base.models import DifficultyLevel, KnowledgeCategory, KnowledgeSearchQuery
from app.knowledge_base.search import KnowledgeSearchEngine
from tests.knowledge_base.conftest import make_entry


def test_by_category(entries, entry_fvg) -> None:
    results = KnowledgeSearchEngine().by_category(entries, KnowledgeCategory.FAIR_VALUE_GAPS)
    assert results == (entry_fvg,)


def test_by_keyword_matches_title_summary_or_content() -> None:
    entries = (make_entry("a", title="Gap concept", summary="s", content="c"), make_entry("b", title="unrelated", summary="s", content="c"))
    results = KnowledgeSearchEngine().by_keyword(entries, "gap")
    assert [e.entry_id for e in results] == ["a"]


def test_by_keyword_is_case_insensitive() -> None:
    entries = (make_entry("a", title="Fair Value Gap"),)
    results = KnowledgeSearchEngine().by_keyword(entries, "FAIR value")
    assert len(results) == 1


def test_by_tag(entries, entry_risk) -> None:
    results = KnowledgeSearchEngine().by_tag(entries, "risk")
    assert results == (entry_risk,)


def test_by_tag_is_case_insensitive() -> None:
    entries = (make_entry("a", tags=("SMC",)),)
    results = KnowledgeSearchEngine().by_tag(entries, "smc")
    assert len(results) == 1


def test_by_difficulty(entries, entry_risk) -> None:
    results = KnowledgeSearchEngine().by_difficulty(entries, DifficultyLevel.ADVANCED)
    assert results == (entry_risk,)


def test_by_asset_matches_declared_asset(entries, entry_fvg) -> None:
    results = KnowledgeSearchEngine().by_asset(entries, "forex")
    assert entry_fvg in results


def test_by_asset_universal_entry_matches_any_asset(entries, entry_risk) -> None:
    # entry_risk has no declared asset_classes -- it's universal
    results = KnowledgeSearchEngine().by_asset(entries, "crypto")
    assert entry_risk in results


def test_by_timeframe_matches_declared_timeframe(entries, entry_fvg) -> None:
    results = KnowledgeSearchEngine().by_timeframe(entries, "H1")
    assert entry_fvg in results


def test_by_timeframe_universal_entry_matches_any_timeframe(entries, entry_risk) -> None:
    results = KnowledgeSearchEngine().by_timeframe(entries, "M1")
    assert entry_risk in results


def test_by_session_matches_declared_session(entries, entry_fvg) -> None:
    results = KnowledgeSearchEngine().by_session(entries, "London")
    assert entry_fvg in results


def test_by_session_universal_entry_matches_any_session(entries, entry_risk) -> None:
    results = KnowledgeSearchEngine().by_session(entries, "Tokyo")
    assert entry_risk in results


def test_empty_query_returns_every_entry(entries) -> None:
    results = KnowledgeSearchEngine().search(entries, KnowledgeSearchQuery())
    assert set(results) == set(entries)


def test_search_and_combines_every_field(entries, entry_fvg) -> None:
    query = KnowledgeSearchQuery(category=KnowledgeCategory.FAIR_VALUE_GAPS, difficulty=DifficultyLevel.BEGINNER, tag="smc")
    results = KnowledgeSearchEngine().search(entries, query)
    assert results == (entry_fvg,)


def test_search_returns_empty_when_no_match(entries) -> None:
    query = KnowledgeSearchQuery(keyword="nonexistent-keyword-xyz")
    assert KnowledgeSearchEngine().search(entries, query) == ()
