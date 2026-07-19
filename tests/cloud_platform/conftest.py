"""Shared fixtures for `tests/cloud_platform/`."""

import pytest

from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft
from app.cloud_platform.models import ArtifactReference, DatasetReference, ProjectReference, ResearchReference
from app.cloud_platform.artifact_manager import CloudArtifactManager
from app.cloud_platform.version_manager import CloudVersionManager
from app.cloud_platform.workspace_manager import CloudWorkspaceManager
from app.core.checksums import compute_checksum


def _fake_checksum(seed: str) -> str:
    """A well-formed 64-char SHA-256 hex digest, deterministic per `seed`."""
    return compute_checksum({"seed": seed})


@pytest.fixture
def dataset_reference() -> DatasetReference:
    return DatasetReference(reference_id="dataset-1", name="XAUUSD_M5", symbol="XAUUSD", timeframe="M5", checksum=_fake_checksum("dataset-1"))


@pytest.fixture
def artifact_reference() -> ArtifactReference:
    return ArtifactReference(reference_id="artifact-1", name="EA_Alpha", artifact_type="EA_SOURCE", checksum=_fake_checksum("artifact-1"))


@pytest.fixture
def research_reference() -> ResearchReference:
    return ResearchReference(reference_id="research-1", name="Trend Study", checksum=_fake_checksum("research-1"))


@pytest.fixture
def project_reference() -> ProjectReference:
    return ProjectReference(reference_id="project-ref-1", name="Shared Project", checksum=_fake_checksum("project-ref-1"))


@pytest.fixture
def project_draft(dataset_reference, artifact_reference, research_reference) -> ProjectDraft:
    return ProjectDraft(
        project_id="project-1",
        name="Alpha Strategy",
        research_references=(research_reference,),
        dataset_references=(dataset_reference,),
        artifact_references=(artifact_reference,),
    )


@pytest.fixture
def snapshot_draft() -> SnapshotDraft:
    return SnapshotDraft(snapshot_id="snapshot-1", label="Initial capture", project_ids=("project-1",))


@pytest.fixture
def cloud_platform_context(project_draft, snapshot_draft) -> CloudPlatformContext:
    return CloudPlatformContext(workspace_id="workspace-1", label="Test Workspace", projects=(project_draft,), snapshots=(snapshot_draft,))


@pytest.fixture
def workspace_manager() -> CloudWorkspaceManager:
    return CloudWorkspaceManager()


@pytest.fixture
def created_workspace(workspace_manager: CloudWorkspaceManager):
    return workspace_manager.create_workspace("ws-1", label="Research Workspace")


@pytest.fixture
def artifact_manager() -> CloudArtifactManager:
    return CloudArtifactManager()


@pytest.fixture
def version_manager() -> CloudVersionManager:
    return CloudVersionManager()
