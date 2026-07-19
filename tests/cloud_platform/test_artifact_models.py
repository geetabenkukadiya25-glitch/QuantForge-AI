"""`app.cloud_platform.artifact`: immutability, serialization, field constraints."""

import pytest
from pydantic import ValidationError

from app.cloud_platform.artifact import ArtifactHistoryEvent, ArtifactHistoryEventType, ArtifactRecord, ArtifactStatus, ArtifactType


def test_artifact_record_is_frozen(artifact_manager) -> None:
    record = artifact_manager.create_artifact("a1", ArtifactType.DATASET, "Dataset A")
    with pytest.raises(ValidationError):
        record.notes = "hacked"


def test_artifact_record_rejects_unknown_fields(artifact_manager) -> None:
    record = artifact_manager.create_artifact("a1", ArtifactType.DATASET, "Dataset A")
    with pytest.raises(ValidationError):
        type(record)(**{**record.model_dump(), "extra_field": "nope"})


def test_artifact_record_requires_non_empty_id() -> None:
    with pytest.raises(ValidationError):
        ArtifactRecord(artifact_id="", artifact_type=ArtifactType.DATASET, name="A", checksum="x" * 64)


def test_artifact_record_requires_non_empty_name() -> None:
    with pytest.raises(ValidationError):
        ArtifactRecord(artifact_id="a1", artifact_type=ArtifactType.DATASET, name="", checksum="x" * 64)


def test_artifact_record_defaults() -> None:
    record = ArtifactRecord(artifact_id="a1", artifact_type=ArtifactType.DATASET, name="A", checksum="x" * 64)
    assert record.status == ArtifactStatus.ACTIVE
    assert record.is_favorite is False
    assert record.version == 1
    assert record.tags == ()
    assert record.dependencies == ()
    assert record.references == ()
    assert record.metadata == {}
    assert record.history == ()


def test_history_event_requires_non_empty_ids() -> None:
    with pytest.raises(ValidationError):
        ArtifactHistoryEvent(event_id="", event_type=ArtifactHistoryEventType.CREATED, artifact_id="a1", version=1, checksum="x" * 64)


def test_artifact_type_covers_every_required_type() -> None:
    required = {
        "DATASET", "STRATEGY", "SDL", "COMPILED_STRATEGY", "BACKTEST_RESULT", "OPTIMIZATION_RESULT",
        "VALIDATION_RESULT", "REPLAY_RESULT", "RESEARCH_RESULT", "KNOWLEDGE_RESULT", "PORTFOLIO_RESULT",
        "EA_GENERATOR_RESULT", "CLOUD_SNAPSHOT", "WORKSPACE_SNAPSHOT", "REPORT", "STATISTICS",
        "CONFIGURATION", "DOCUMENTATION", "CUSTOM",
    }
    assert {t.value for t in ArtifactType} == required


def test_artifact_status_enum_values() -> None:
    assert {s.value for s in ArtifactStatus} == {"ACTIVE", "ARCHIVED", "DELETED"}
