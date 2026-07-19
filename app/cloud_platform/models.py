"""Immutable models for the Cloud Platform Foundation.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
The Cloud Platform is a management layer: it stores references (ids,
names, checksums, free-text descriptions) to artifacts produced by other
engines, and never inspects, recomputes, or depends on those artifacts'
internals. `CloudBuild` is the single deterministic, checksummed artifact
this engine produces.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.cloud_platform.metadata import WorkspaceMetadata


class CloudPlatformModel(BaseModel):
    """Base class for every cloud_platform model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ReferenceKind(str, Enum):
    PROJECT = "PROJECT"
    RESEARCH = "RESEARCH"
    DATASET = "DATASET"
    ARTIFACT = "ARTIFACT"


class ProjectReference(CloudPlatformModel):
    """A reference to another project, by id/name/checksum only -- no project internals."""

    reference_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    checksum: str = Field(min_length=1, description="The referenced project's own content checksum, supplied by the caller.")
    description: str = ""


class ResearchReference(CloudPlatformModel):
    """A reference to a Research Engine output. Carries no research internals -- id, name, and checksum only."""

    reference_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    checksum: str = Field(min_length=1, description="The referenced research result's own content checksum, supplied by the caller.")
    description: str = ""


class DatasetReference(CloudPlatformModel):
    """A reference to a historical dataset. Carries no dataset internals -- id, name, symbol/timeframe labels, and checksum only."""

    reference_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    symbol: str | None = None
    timeframe: str | None = None
    checksum: str = Field(min_length=1, description="The referenced dataset's own content checksum, supplied by the caller.")
    description: str = ""


class ArtifactReference(CloudPlatformModel):
    """A reference to any generated artifact (EA source, report, snapshot export, ...)."""

    reference_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1, description='Free-text label, e.g. "EA_SOURCE", "BACKTEST_REPORT", "VALIDATION_REPORT".')
    checksum: str = Field(min_length=1, description="The referenced artifact's own content checksum, supplied by the caller.")
    description: str = ""


class CloudProject(CloudPlatformModel):
    """One project grouping of references within a workspace."""

    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    research_references: tuple[ResearchReference, ...] = Field(default_factory=tuple)
    dataset_references: tuple[DatasetReference, ...] = Field(default_factory=tuple)
    artifact_references: tuple[ArtifactReference, ...] = Field(default_factory=tuple)
    checksum: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_reference_count(self) -> int:
        return len(self.research_references) + len(self.dataset_references) + len(self.artifact_references)


class CloudSnapshot(CloudPlatformModel):
    """A point-in-time capture of which projects a workspace held, by id."""

    snapshot_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    label: str = ""
    project_ids: tuple[str, ...] = Field(default_factory=tuple)
    checksum: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CloudWorkspace(CloudPlatformModel):
    """The complete, immutable state of one compiled workspace: its projects and snapshots."""

    workspace_id: str = Field(min_length=1)
    metadata: WorkspaceMetadata
    projects: tuple[CloudProject, ...] = Field(default_factory=tuple)
    project_references: tuple[ProjectReference, ...] = Field(
        default_factory=tuple, description="Cross-references to OTHER workspaces' projects, by id/checksum only."
    )
    snapshots: tuple[CloudSnapshot, ...] = Field(default_factory=tuple)
    checksum: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CloudStatistics(CloudPlatformModel):
    """Aggregate, at-a-glance statistics for one compiled workspace."""

    workspace_count: int = Field(ge=0, default=1, description="Always 1 for a single CloudBuild; registry-wide aggregation reports this across many builds.")
    project_count: int = Field(ge=0, default=0)
    snapshot_count: int = Field(ge=0, default=0)
    research_reference_count: int = Field(ge=0, default=0)
    dataset_reference_count: int = Field(ge=0, default=0)
    artifact_reference_count: int = Field(ge=0, default=0)
    checksum: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CloudBuild(CloudPlatformModel):
    """The complete, immutable outcome of one workspace compilation.

    Immutable, serializable, versioned, and hashable -- the single
    deterministic artifact this engine produces (`CloudPlatformResult`).
    """

    result_id: str = Field(min_length=1)
    metadata: WorkspaceMetadata
    workspace: CloudWorkspace
    statistics: CloudStatistics
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CloudReport(CloudPlatformModel):
    """An executive, numbers-only summary of one `CloudBuild`. No charts. No UI."""

    report_id: str = Field(min_length=1)
    result_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    workspace_label: str = ""
    project_count: int = Field(ge=0)
    snapshot_count: int = Field(ge=0)
    research_reference_count: int = Field(ge=0)
    dataset_reference_count: int = Field(ge=0)
    artifact_reference_count: int = Field(ge=0)
    checksum: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
