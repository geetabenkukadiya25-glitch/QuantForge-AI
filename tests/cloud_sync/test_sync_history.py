"""`SyncHistoryStore` -- mirrors `WorkflowHistoryStore`'s coverage."""

from pathlib import Path

from app.cloud_sync.cloud_models import SyncKind, SyncOperation
from app.cloud_sync.sync_history import SyncHistoryStore


def test_record_and_list_records(tmp_path: Path) -> None:
    store = SyncHistoryStore(tmp_path)
    op = SyncOperation(kind=SyncKind.DATASET, object_id="d-1")
    store.record(op)

    records = store.list_records(op.id)
    assert len(records) == 1
    assert records[0].id == op.id


def test_filters_by_operation_id(tmp_path: Path) -> None:
    store = SyncHistoryStore(tmp_path)
    a = SyncOperation(kind=SyncKind.DATASET, object_id="d-1")
    b = SyncOperation(kind=SyncKind.DATASET, object_id="d-2")
    store.record(a)
    store.record(b)
    assert len(store.list_records(a.id)) == 1
    assert len(store.list_records()) == 2


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = SyncHistoryStore(tmp_path)
    store.record(SyncOperation(kind=SyncKind.DATASET, object_id="d-1"))
    (tmp_path / "cloud_sync_history.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_records() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = SyncHistoryStore(tmp_path)
    assert store.list_records() == []
