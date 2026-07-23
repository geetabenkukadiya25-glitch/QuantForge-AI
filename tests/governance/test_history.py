"""`GovernanceHistoryStore` -- mirrors `WorkflowHistoryStore`'s coverage."""

from pathlib import Path

from app.governance.governance_models import GovernanceRecord, GovernedObjectType
from app.governance.history import GovernanceHistoryStore


def test_record_and_list_records(tmp_path: Path) -> None:
    store = GovernanceHistoryStore(tmp_path)
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    store.record(record)

    records = store.list_records(record.id)
    assert len(records) == 1
    assert records[0].id == record.id


def test_filters_by_record_id(tmp_path: Path) -> None:
    store = GovernanceHistoryStore(tmp_path)
    a = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    b = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-2")
    store.record(a)
    store.record(b)
    assert len(store.list_records(a.id)) == 1
    assert len(store.list_records()) == 2


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = GovernanceHistoryStore(tmp_path)
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    store.record(record)
    (tmp_path / "governance_history.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_records() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = GovernanceHistoryStore(tmp_path)
    assert store.list_records() == []
