"""`app.dataset_manager.search`: pure search/filter functions."""

from datetime import datetime, timezone

from app.dataset_manager.models import DatasetRecord, DatasetSource
from app.dataset_manager.search import filter_records, search_records

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(id_: str, filename: str, symbol: str, tags: list[str], favorite: bool = False, archived: bool = False) -> DatasetRecord:
    return DatasetRecord(
        id=id_, filename=filename, display_name=filename, import_date=NOW, created=NOW, modified=NOW,
        file_size=1, rows=1, columns=1, candles=1, symbol=symbol, timeframe="H1", hash=id_, source=DatasetSource.UPLOAD,
        tags=tags, favorite=favorite, archived=archived,
    )


def test_search_matches_filename_symbol_and_tags() -> None:
    records = [
        _record("1", "eurusd_h1.csv", "EURUSD", ["Forex"]),
        _record("2", "xauusd_m15.csv", "XAUUSD", ["Gold", "Scalping"]),
    ]
    assert [r.id for r in search_records(records, "eurusd")] == ["1"]
    assert [r.id for r in search_records(records, "gold")] == ["2"]
    assert [r.id for r in search_records(records, "scalping")] == ["2"]


def test_search_empty_query_returns_all() -> None:
    records = [_record("1", "a.csv", "A", []), _record("2", "b.csv", "B", [])]
    assert search_records(records, "") == records


def test_filter_by_favorite_and_archived() -> None:
    records = [
        _record("1", "a.csv", "A", [], favorite=True, archived=False),
        _record("2", "b.csv", "B", [], favorite=False, archived=True),
    ]
    assert [r.id for r in filter_records(records, favorite=True)] == ["1"]
    assert [r.id for r in filter_records(records, archived=True)] == ["2"]


def test_filter_by_tags_and_source() -> None:
    records = [
        _record("1", "a.csv", "A", ["Forex"]),
        _record("2", "b.csv", "B", ["Gold"]),
    ]
    assert [r.id for r in filter_records(records, tags=["gold"])] == ["2"]
    assert [r.id for r in filter_records(records, source=DatasetSource.UPLOAD.value)] == ["1", "2"]
