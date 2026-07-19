"""Immutable data models for the offline Project Versioning & Snapshot
System (Phase 17.3).

This is NOT Git. This is NOT source-code versioning. It is an internal,
deterministic version-history layer over objects already managed
elsewhere in QuantForge AI (workspaces via
`app.cloud_platform.workspace_manager`, artifacts via
`app.cloud_platform.artifact_manager`, and any future object type). It
never holds the versioned subject's own content -- only a
`snapshot_checksum` identifying that content's state at a point in
time, plus lineage (`parent_version`), lifecycle state, and history.
Every model here is frozen; every mutation elsewhere in this phase
produces a brand-new record rather than mutating one in place.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import Field

from app.cloud_platform.models import CloudPlatformModel

VERSION_SCHEMA_VERSION = "1.0.0"


class VersionSubjectType(str, Enum):
    """What kind of object a `VersionRecord` tracks the lineage of."""

    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"
    ARTIFACT = "ARTIFACT"
    RESEARCH = "RESEARCH"
    STRATEGY = "STRATEGY"
    PORTFOLIO = "PORTFOLIO"
    KNOWLEDGE = "KNOWLEDGE"
    BACKTEST = "BACKTEST"
    OPTIMIZATION = "OPTIMIZATION"
    VALIDATION = "VALIDATION"
    REPLAY = "REPLAY"
    EA_GENERATOR = "EA_GENERATOR"
    REPORT = "REPORT"
    STATISTICS = "STATISTICS"
    CUSTOM = "CUSTOM"  # reserved for future object types


class VersionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"  # soft delete only -- a record is never physically removed


class VersionHistoryEventType(str, Enum):
    CREATED = "CREATED"
    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"
    RESTORED = "RESTORED"
    ARCHIVED = "ARCHIVED"
    RESTORED_STATUS = "RESTORED_STATUS"
    DELETED = "DELETED"
    FAVORITE_CHANGED = "FAVORITE_CHANGED"
    TAG_CHANGED = "TAG_CHANGED"
    NOTES_UPDATED = "NOTES_UPDATED"
    METADATA_UPDATED = "METADATA_UPDATED"
    REFERENCE_UPDATED = "REFERENCE_UPDATED"
    COMPARED = "COMPARED"


class VersionHistory(CloudPlatformModel):
    """One immutable, checksummed entry in a version's append-only history.

    `checksum` covers `event_type`/`version_id`/`message` only --
    `event_id` (random) and `timestamp` (wall-clock) are excluded, so
    replaying the same sequence of operations always produces the same
    sequence of event checksums.
    """

    event_id: str = Field(min_length=1)
    event_type: VersionHistoryEventType
    version_id: str = Field(min_length=1)
    message: str = ""
    checksum: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VersionReference(CloudPlatformModel):
    """A checksum-only pointer from one version to another specific version
    (of the same or a different subject) -- never the referenced
    version's own content."""

    reference_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1, description="The target version_id being referenced.")
    subject_type: VersionSubjectType
    subject_id: str = Field(min_length=1)
    checksum: str = Field(min_length=1, description="The referenced version's own snapshot_checksum, supplied by the caller.")
    description: str = ""


class VersionSnapshot(CloudPlatformModel):
    """A point-in-time capture of one version's content identity.

    Never holds the subject's actual content -- only the
    `snapshot_checksum` identifying it, so `restore_snapshot` can later
    create a brand-new version carrying the same content identity
    without this system ever inspecting what that content actually is.
    """

    snapshot_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    subject_type: VersionSubjectType
    subject_id: str = Field(min_length=1)
    snapshot_checksum: str = Field(min_length=1)
    label: str = ""
    created_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VersionRecord(CloudPlatformModel):
    """The complete, immutable, checksummed state of one version.

    `version_id` is this version's own stable identity (subsequent
    lifecycle mutations replace the CURRENT record for this id, exactly
    like `app.cloud_platform.workspace.WorkspaceRecord`/
    `app.cloud_platform.artifact.ArtifactRecord` -- each individual
    record object is itself always frozen and never mutated in place).
    `parent_version` links this version into its subject's lineage,
    forming a tree (branches are allowed: multiple versions may share
    the same parent). `snapshot_checksum` is the content identity of the
    versioned subject at this point -- never the content itself.
    """

    version_id: str = Field(min_length=1)
    subject_type: VersionSubjectType
    subject_id: str = Field(min_length=1)
    parent_version: str | None = None
    version_number: int = Field(ge=1)
    created_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checksum: str = Field(min_length=1)
    snapshot_checksum: str = Field(min_length=1)
    workspace_id: str | None = None
    project_id: str | None = None
    artifact_id: str | None = None
    change_summary: str = ""
    author: str = Field(default="", description="Free-text, offline display label. Not an authenticated identity.")
    status: VersionStatus = VersionStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    references: tuple[VersionReference, ...] = Field(default_factory=tuple)
    history: tuple[VersionHistory, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    notes: str = ""
    is_favorite: bool = False
    schema_version: str = VERSION_SCHEMA_VERSION


class VersionComparison(CloudPlatformModel):
    """The deterministic outcome of comparing two `VersionRecord`s."""

    comparison_id: str = Field(min_length=1)
    version_id_a: str = Field(min_length=1)
    version_id_b: str = Field(min_length=1)
    checksum_equal: bool
    snapshot_checksum_equal: bool
    metadata_equal: bool
    references_equal: bool
    history_equal: bool
    dependencies_equal: bool | None = Field(default=None, description="None when dependencies aren't resolvable for this subject type.")
    version_number_delta: int
    created_time_delta_seconds: float
    differences: tuple[str, ...] = Field(default_factory=tuple, description="Names of the fields found to differ.")
    compared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_identical(self) -> bool:
        return len(self.differences) == 0


class VersionSummary(CloudPlatformModel):
    """A lightweight, at-a-glance view of one `VersionRecord` -- used for
    timelines and trees without carrying the full metadata/history/
    references payload."""

    version_id: str = Field(min_length=1)
    subject_type: VersionSubjectType
    subject_id: str = Field(min_length=1)
    parent_version: str | None = None
    version_number: int = Field(ge=1)
    checksum: str = Field(min_length=1)
    status: VersionStatus
    is_favorite: bool = False
    change_summary: str = ""
    created_time: datetime
