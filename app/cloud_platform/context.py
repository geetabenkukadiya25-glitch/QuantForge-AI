"""The standardized input the Cloud Platform's compiler consumes.

`CloudPlatformContext` bundles a workspace's caller-supplied draft state
-- an id, an optional free-text label, and a set of `ProjectDraft`s
naming their own references -- exactly what "manages references" needs
and nothing more. It carries no dataset, no strategy, no report, and no
engine object of any kind: only ids, names, and checksums supplied by
the caller. It is never mutated once built.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.cloud_platform.models import ArtifactReference, DatasetReference, ProjectReference, ResearchReference


@dataclass(frozen=True)
class ProjectDraft:
    """One project's caller-supplied identity and references, before compilation."""

    project_id: str
    name: str
    research_references: tuple[ResearchReference, ...] = ()
    dataset_references: tuple[DatasetReference, ...] = ()
    artifact_references: tuple[ArtifactReference, ...] = ()
    created_at: datetime | None = None


@dataclass(frozen=True)
class SnapshotDraft:
    """One snapshot's caller-supplied identity, before compilation."""

    snapshot_id: str
    label: str = ""
    project_ids: tuple[str, ...] = ()
    created_at: datetime | None = None


@dataclass(frozen=True)
class CloudPlatformContext:
    """Immutable wrapper around one workspace compilation's draft input."""

    workspace_id: str
    label: str = ""
    projects: tuple[ProjectDraft, ...] = field(default_factory=tuple)
    project_references: tuple[ProjectReference, ...] = field(default_factory=tuple)
    snapshots: tuple[SnapshotDraft, ...] = field(default_factory=tuple)
