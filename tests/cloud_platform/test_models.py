"""`app.cloud_platform.models`: immutability, serialization, and field constraints."""

import pytest
from pydantic import ValidationError

from app.cloud_platform.models import ArtifactReference, CloudProject, DatasetReference, ResearchReference


def test_dataset_reference_is_frozen(dataset_reference: DatasetReference) -> None:
    with pytest.raises(ValidationError):
        dataset_reference.symbol = "EURUSD"


def test_dataset_reference_rejects_unknown_fields(dataset_reference: DatasetReference) -> None:
    with pytest.raises(ValidationError):
        DatasetReference(**{**dataset_reference.model_dump(), "extra_field": "nope"})


def test_reference_requires_non_empty_checksum() -> None:
    with pytest.raises(ValidationError):
        ArtifactReference(reference_id="a1", name="A", artifact_type="EA_SOURCE", checksum="")


def test_reference_requires_non_empty_name() -> None:
    with pytest.raises(ValidationError):
        ResearchReference(reference_id="r1", name="", checksum="x" * 64)


def test_cloud_project_total_reference_count(dataset_reference, artifact_reference, research_reference) -> None:
    project = CloudProject(
        project_id="p1",
        name="Alpha",
        research_references=(research_reference,),
        dataset_references=(dataset_reference,),
        artifact_references=(artifact_reference,),
        checksum="x" * 64,
    )
    assert project.total_reference_count == 3


def test_models_round_trip_through_dict(dataset_reference: DatasetReference) -> None:
    payload = dataset_reference.model_dump(mode="json")
    rebuilt = DatasetReference(**payload)
    assert rebuilt == dataset_reference
