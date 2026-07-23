"""Pure search/filter functions over `CatalogRecord` lists (Phase 17.5),
mirroring `app.dataset_manager.search`'s shape -- no state, no I/O,
trivially testable.
"""

from app.data_catalog.models import CatalogRecord


def search_catalog(entries: list[CatalogRecord], query: str) -> list[CatalogRecord]:
    """Case-insensitive substring match across uuid, filename, display
    name, tags, description, and owner."""
    if not query.strip():
        return list(entries)
    needle = query.strip().lower()

    def _matches(entry: CatalogRecord) -> bool:
        haystacks = [entry.id, entry.filename, entry.display_name, entry.description, entry.owner, *entry.tags]
        return any(needle in h.lower() for h in haystacks)

    return [e for e in entries if _matches(e)]


def filter_catalog(
    entries: list[CatalogRecord],
    *,
    favorite: bool | None = None,
    archived: bool | None = None,
    protected: bool | None = None,
    recently_used: bool | None = None,
    min_quality: int | None = None,
) -> list[CatalogRecord]:
    result = entries
    if favorite is not None:
        result = [e for e in result if e.favorite == favorite]
    if archived is not None:
        result = [e for e in result if e.archived == archived]
    if protected is not None:
        result = [e for e in result if e.protected == protected]
    if recently_used is not None:
        result = [e for e in result if (e.last_used is not None) == recently_used]
    if min_quality is not None:
        result = [e for e in result if e.quality_score >= min_quality]
    return result
