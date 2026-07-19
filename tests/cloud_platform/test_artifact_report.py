"""`app.cloud_platform.artifact_report`: executive/artifact/dependency/
history/statistics/validation summaries. No charts."""

import pandas as pd

from app.cloud_platform.artifact import ArtifactType
from app.cloud_platform.artifact_manager import CloudArtifactManager
from app.cloud_platform.artifact_report import ArtifactReport


def _built_records(manager: CloudArtifactManager):
    dataset = manager.create_artifact("a1", ArtifactType.DATASET, "Dataset A", source_module="data_engine")
    strategy = manager.create_artifact("a2", ArtifactType.STRATEGY, "Strategy B", dependencies=(dataset.artifact_id,))
    manager.favorite_artifact("a2", True)
    return manager.get_artifact("a2")


def test_artifact_summary_matches_record() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    summary = ArtifactReport(record, manager.registry).artifact_summary()
    assert summary["artifact_id"] == "a2"
    assert summary["is_favorite"] is True
    assert summary["checksum"] == record.checksum


def test_dependency_summary_resolves_against_registry() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    frame = ArtifactReport(record, manager.registry).dependency_summary()
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1
    assert frame.iloc[0]["dependency_id"] == "a1"
    assert frame.iloc[0]["name"] == "Dataset A"


def test_dependency_summary_without_registry_is_id_only() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    frame = ArtifactReport(record).dependency_summary()
    assert list(frame.columns) == ["dependency_id"]


def test_history_summary_covers_every_event() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    frame = ArtifactReport(record).history_summary()
    assert len(frame) == len(record.history)


def test_statistics_summary_uses_registry_when_supplied() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    summary = ArtifactReport(record, manager.registry).statistics_summary()
    assert summary["artifact_count"] == 2


def test_statistics_summary_falls_back_to_single_record() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    summary = ArtifactReport(record).statistics_summary()
    assert summary["artifact_count"] == 1


def test_validation_summary_reports_valid() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    summary = ArtifactReport(record, manager.registry).validation_summary()
    assert summary["is_valid"] is True


def test_executive_summary_combines_every_section() -> None:
    manager = CloudArtifactManager()
    record = _built_records(manager)
    summary = ArtifactReport(record, manager.registry).executive_summary()
    assert set(summary.keys()) == {"artifact", "statistics", "validation", "dependency_count", "history_count"}
    assert summary["dependency_count"] == 1
