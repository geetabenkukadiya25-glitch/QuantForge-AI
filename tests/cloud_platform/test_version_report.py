"""`app.cloud_platform.version_report`: executive/version/snapshot/
comparison/history/statistics/validation summaries. No charts."""

import pandas as pd

from app.cloud_platform.version_manager import CloudVersionManager
from app.cloud_platform.version_report import VersionReport
from app.cloud_platform.versioning import VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def _built_record(manager: CloudVersionManager):
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1), change_summary="init")
    manager.snapshot("v1", label="checkpoint")
    return manager.favorite_version("v1", True)


def test_version_summary_matches_record() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    summary = VersionReport(record, manager.registry).version_summary()
    assert summary["version_id"] == "v1"
    assert summary["is_favorite"] is True
    assert summary["checksum"] == record.checksum


def test_snapshot_summary_lists_registered_snapshots() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    frame = VersionReport(record, manager.registry).snapshot_summary()
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1
    assert frame.iloc[0]["label"] == "checkpoint"


def test_snapshot_summary_without_registry_is_empty() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    frame = VersionReport(record).snapshot_summary()
    assert frame.empty


def test_comparison_summary_is_a_plain_dict() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    comparison = manager.compare_versions("v1", "v2")
    summary = VersionReport(manager.get_version("v1")).comparison_summary(comparison)
    assert summary["version_id_a"] == "v1"
    assert summary["version_id_b"] == "v2"


def test_history_summary_covers_every_event() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    frame = VersionReport(record).history_summary()
    assert len(frame) == len(record.history)


def test_statistics_summary_uses_registry_when_supplied() -> None:
    manager = CloudVersionManager()
    manager.create_version("v0", VersionSubjectType.ARTIFACT, "a0", _cs(0))
    record = _built_record(manager)
    summary = VersionReport(record, manager.registry).statistics_summary()
    assert summary["version_count"] == 2


def test_statistics_summary_falls_back_to_single_record() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    summary = VersionReport(record).statistics_summary()
    assert summary["version_count"] == 1


def test_validation_summary_reports_valid() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    summary = VersionReport(record, manager.registry).validation_summary()
    assert summary["is_valid"] is True


def test_executive_summary_combines_every_section() -> None:
    manager = CloudVersionManager()
    record = _built_record(manager)
    summary = VersionReport(record, manager.registry).executive_summary()
    assert set(summary.keys()) == {"version", "statistics", "validation", "history_count"}
