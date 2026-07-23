"""Pure search/filter functions over `DatasetRecord` lists (Phase 18.6),
mirroring `app.strategy_library.library_manager`'s `search`/`filter_entries`
shape -- no state, no I/O, trivially testable.
"""

from app.dataset_manager.models import DatasetRecord


def search_records(records: list[DatasetRecord], query: str) -> list[DatasetRecord]:
    """Case-insensitive substring match across filename, display name,
    symbol, timeframe, tags, description, and notes."""
    if not query.strip():
        return list(records)
    needle = query.strip().lower()

    def _matches(record: DatasetRecord) -> bool:
        haystacks = [
            record.filename,
            record.display_name,
            record.symbol or "",
            record.timeframe or "",
            record.description,
            record.notes,
            *record.tags,
        ]
        return any(needle in h.lower() for h in haystacks)

    return [r for r in records if _matches(r)]


def filter_records(
    records: list[DatasetRecord],
    *,
    favorite: bool | None = None,
    archived: bool | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
) -> list[DatasetRecord]:
    result = records
    if favorite is not None:
        result = [r for r in result if r.favorite == favorite]
    if archived is not None:
        result = [r for r in result if r.archived == archived]
    if tags:
        wanted = {t.lower() for t in tags}
        result = [r for r in result if wanted & {t.lower() for t in r.tags}]
    if source is not None:
        result = [r for r in result if r.source.value == source]
    return result
