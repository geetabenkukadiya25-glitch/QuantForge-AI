"""`app.data_catalog.search` -- pure search/filter over `CatalogRecord`."""

from datetime import datetime, timezone

from app.data_catalog.models import CatalogRecord
from app.data_catalog.search import filter_catalog, search_catalog

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _entry(**overrides) -> CatalogRecord:
    defaults = dict(
        id="abc-123",
        filename="EURUSD_H1.csv",
        display_name="EURUSD Hourly",
        description="",
        owner="Alice",
        created=NOW,
        modified=NOW,
        imported=NOW,
        last_used=None,
        source="UPLOAD",
        hash="deadbeef",
        version_count=1,
        tags=("Forex",),
        quality_score=90,
        favorite=False,
        archived=False,
        protected=False,
    )
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_search_matches_filename_symbol_owner_and_tag() -> None:
    entries = [_entry()]
    assert search_catalog(entries, "eurusd") == entries
    assert search_catalog(entries, "Alice") == entries
    assert search_catalog(entries, "Forex") == entries
    assert search_catalog(entries, "nonexistent") == []


def test_search_empty_query_returns_all() -> None:
    entries = [_entry(), _entry(id="def-456")]
    assert search_catalog(entries, "  ") == entries


def test_filter_by_favorite_archived_protected_quality() -> None:
    fav = _entry(id="fav", favorite=True)
    archived = _entry(id="archived", archived=True)
    protected = _entry(id="protected", protected=True)
    low_quality = _entry(id="low", quality_score=40)
    entries = [fav, archived, protected, low_quality]

    assert filter_catalog(entries, favorite=True) == [fav]
    assert filter_catalog(entries, archived=True) == [archived]
    assert filter_catalog(entries, protected=True) == [protected]
    assert filter_catalog(entries, min_quality=80) == [fav, archived, protected]


def test_filter_by_recently_used() -> None:
    used = _entry(id="used", last_used=NOW)
    unused = _entry(id="unused", last_used=None)
    entries = [used, unused]
    assert filter_catalog(entries, recently_used=True) == [used]
    assert filter_catalog(entries, recently_used=False) == [unused]
