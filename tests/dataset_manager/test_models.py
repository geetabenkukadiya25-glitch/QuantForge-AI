"""`app.dataset_manager.models`: round-trip `to_dict`/`from_dict` for
every persisted dataclass."""

from datetime import datetime, timezone

from app.dataset_manager.models import (
    DatasetAuditEvent,
    DatasetAuditEventType,
    DatasetHealth,
    DatasetManagerState,
    DatasetRecord,
    DatasetSource,
    DatasetStatistics,
    DatasetVersion,
    DatasetVersionEventType,
    HealthCheck,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(record_id: str = "abc123") -> DatasetRecord:
    return DatasetRecord(
        id=record_id,
        filename="eurusd.csv",
        display_name="EURUSD H1",
        import_date=NOW,
        created=NOW,
        modified=NOW,
        file_size=1024,
        rows=100,
        columns=7,
        candles=100,
        symbol="EURUSD",
        timeframe="H1",
        hash="deadbeef",
        source=DatasetSource.UPLOAD,
        tags=["Forex"],
    )


def test_dataset_record_round_trip() -> None:
    record = _record()
    restored = DatasetRecord.from_dict(record.to_dict())
    assert restored == record


def test_dataset_statistics_round_trip() -> None:
    stats = DatasetStatistics(
        rows=10, columns=7, candles=10, date_range_start="2024-01-01", date_range_end="2024-01-02",
        symbol="EURUSD", timeframe="H1", sessions=2, memory_usage_bytes=1000, disk_size_bytes=500, frequency="H1",
    )
    assert DatasetStatistics.from_dict(stats.to_dict()) == stats


def test_dataset_health_round_trip() -> None:
    health = DatasetHealth(
        score=90,
        checks=(HealthCheck(name="sorting", passed=True, message="ok"),),
        warnings=("w1",),
        errors=(),
        suggestions=("s1",),
    )
    assert DatasetHealth.from_dict(health.to_dict()) == health


def test_dataset_version_round_trip() -> None:
    version = DatasetVersion(event_type=DatasetVersionEventType.IMPORTED, timestamp=NOW, note="first import")
    assert DatasetVersion.from_dict(version.to_dict()) == version


def test_dataset_audit_event_round_trip() -> None:
    event = DatasetAuditEvent(event_type=DatasetAuditEventType.DELETED, key="abc123", timestamp=NOW)
    assert DatasetAuditEvent.from_dict(event.to_dict()) == event


def test_dataset_manager_state_round_trip() -> None:
    record = _record()
    state = DatasetManagerState(
        records={record.id: record},
        versions={record.id: [DatasetVersion(event_type=DatasetVersionEventType.IMPORTED, timestamp=NOW)]},
    )
    restored = DatasetManagerState.from_dict(state.to_dict())
    assert restored.records[record.id] == record
    assert restored.versions[record.id][0].event_type == DatasetVersionEventType.IMPORTED
