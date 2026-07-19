"""`app.cloud_platform.versioning`: immutability, serialization, field constraints."""

import pytest
from pydantic import ValidationError

from app.cloud_platform.versioning import VersionHistory, VersionHistoryEventType, VersionRecord, VersionStatus, VersionSubjectType
from app.core.checksums import compute_checksum


def test_version_record_is_frozen(version_manager) -> None:
    record = version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", compute_checksum({"c": 1}))
    with pytest.raises(ValidationError):
        record.notes = "hacked"


def test_version_record_rejects_unknown_fields(version_manager) -> None:
    record = version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", compute_checksum({"c": 1}))
    with pytest.raises(ValidationError):
        type(record)(**{**record.model_dump(), "extra_field": "nope"})


def test_version_record_requires_non_empty_id() -> None:
    with pytest.raises(ValidationError):
        VersionRecord(version_id="", subject_type=VersionSubjectType.WORKSPACE, subject_id="ws1", version_number=1, checksum="x" * 64, snapshot_checksum="y" * 64)


def test_version_record_requires_version_number_ge_1() -> None:
    with pytest.raises(ValidationError):
        VersionRecord(version_id="v1", subject_type=VersionSubjectType.WORKSPACE, subject_id="ws1", version_number=0, checksum="x" * 64, snapshot_checksum="y" * 64)


def test_version_record_defaults() -> None:
    record = VersionRecord(version_id="v1", subject_type=VersionSubjectType.WORKSPACE, subject_id="ws1", version_number=1, checksum="x" * 64, snapshot_checksum="y" * 64)
    assert record.status == VersionStatus.ACTIVE
    assert record.is_favorite is False
    assert record.parent_version is None
    assert record.tags == ()
    assert record.references == ()
    assert record.history == ()
    assert record.metadata == {}


def test_history_event_requires_non_empty_ids() -> None:
    with pytest.raises(ValidationError):
        VersionHistory(event_id="", event_type=VersionHistoryEventType.CREATED, version_id="v1", checksum="x" * 64)


def test_version_subject_type_covers_every_required_subject() -> None:
    required = {
        "WORKSPACE", "PROJECT", "ARTIFACT", "RESEARCH", "STRATEGY", "PORTFOLIO", "KNOWLEDGE",
        "BACKTEST", "OPTIMIZATION", "VALIDATION", "REPLAY", "EA_GENERATOR", "REPORT", "STATISTICS", "CUSTOM",
    }
    assert {t.value for t in VersionSubjectType} == required


def test_version_status_enum_values() -> None:
    assert {s.value for s in VersionStatus} == {"ACTIVE", "ARCHIVED", "DELETED"}
