"""`app.dataset_manager.DatasetManager` integration test -- the full
lifecycle: import -> duplicate-import dedup -> search -> filter ->
favorite -> archive/restore -> revalidate -> reindex -> delete blocked
while protected -> audit log."""

import pytest

from app.dataset_manager.exceptions import ProtectedDatasetError


def test_full_lifecycle(manager, valid_csv_bytes) -> None:
    record = manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    assert record.symbol == "EURUSD"
    assert record.timeframe == "H1"

    # Duplicate import (same content hash) must reuse the existing record.
    duplicate_attempt = manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    assert duplicate_attempt.id == record.id
    assert len(manager.list_entries(archived=None)) == 1

    # Search / filter
    assert [r.id for r in manager.search("EURUSD")] == [record.id]
    assert manager.search("nonexistent") == []
    assert [r.id for r in manager.filter_entries(favorite=False)] == [record.id]

    # Favorite
    updated = manager.toggle_favorite(record.id)
    assert updated.favorite is True
    assert [r.id for r in manager.filter_entries(favorite=True)] == [record.id]

    # Duplicate (a real, distinct copy)
    dup = manager.duplicate(record.id)
    assert dup.id != record.id
    assert len(manager.list_entries(archived=None)) == 2

    # Archive / restore
    manager.archive(record.id)
    assert manager.get(record.id).archived is True
    assert record.id not in [r.id for r in manager.list_entries(archived=False)]
    manager.restore(record.id)
    assert manager.get(record.id).archived is False

    # Revalidate / reindex
    _, health = manager.revalidate(record.id)
    assert 0 <= health.score <= 100
    stats = manager.reindex(record.id)
    assert stats.rows == record.rows

    # Metadata
    manager.set_description(record.id, "Test dataset")
    manager.set_notes(record.id, "Some notes")
    manager.add_tags(record.id, ["Forex", "Scalping"])
    assert set(manager.get(record.id).tags) == {"Forex", "Scalping"}
    manager.remove_tags(record.id, ["Scalping"])
    assert manager.get(record.id).tags == ["Forex"]

    # Rename
    renamed = manager.rename(record.id, "EURUSD Hourly")
    assert renamed.display_name == "EURUSD Hourly"

    # Protected delete is blocked
    manager.set_protected(record.id, True)
    with pytest.raises(ProtectedDatasetError):
        manager.delete(record.id)

    # Unprotect then delete succeeds
    manager.set_protected(record.id, False)
    manager.delete(record.id)
    assert record.id not in [r.id for r in manager.list_entries(archived=None)]

    # Audit log recorded every mutating action for this dataset id
    audit_kinds = {e.event_type.value for e in manager.list_audit_events(record.id)}
    assert {"IMPORTED", "ARCHIVED", "RESTORED", "REVALIDATED", "RENAMED", "DELETED"} <= audit_kinds

    # Version history recorded lifecycle checkpoints for the duplicate
    version_kinds = {v.event_type.value for v in manager.list_versions(dup.id)}
    assert "IMPORTED" in version_kinds


def test_preview_and_load_dataframe(manager, valid_csv_bytes) -> None:
    record = manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    preview = manager.preview(record.id, n=2)
    assert len(preview.rows) == 2
    assert preview.total_rows == record.rows
    assert {c.name for c in preview.columns} >= {"Datetime", "Open", "High", "Low", "Close"}

    df = manager.load_dataframe(record.id)
    assert len(df) == record.rows


def test_record_used_bumps_last_used(manager, valid_csv_bytes) -> None:
    record = manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    assert manager.get(record.id).last_used is None
    manager.record_used(record.id)
    assert manager.get(record.id).last_used is not None
    assert manager.list_recent() == [manager.get(record.id)]


def test_export_round_trip(manager, valid_csv_bytes, tmp_path) -> None:
    record = manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    path = manager.export(record.id, tmp_path / "export.csv", "csv")
    assert path.exists()
    assert any(e.event_type.value == "EXPORTED" for e in manager.list_audit_events(record.id))
