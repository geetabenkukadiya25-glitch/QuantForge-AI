"""Immutable data models for the offline Local Artifact Registry (Phase 17.2).

Reuses -- never duplicates -- the completed Cloud Platform Foundation's
`ArtifactReference` model (`app.cloud_platform.models`) for typed,
external, checksum-only references, and follows the exact same
lifecycle-record discipline `app.cloud_platform.workspace.WorkspaceRecord`
established: an immutable record wrapping content plus status/favorite/
tags/notes/history, with every mutation producing a brand-new record.

This registry stores ONLY metadata and references describing a research
artifact already produced elsewhere in QuantForge AI (`source_module`).
It is NOT cloud storage and NOT a filesystem indexer -- it never reads,
inspects, or depends on the artifact's actual content, and never holds
a filesystem path.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import Field

from app.cloud_platform.models import ArtifactReference, CloudPlatformModel

ARTIFACT_SCHEMA_VERSION = "1.0.0"


class ArtifactType(str, Enum):
    DATASET = "DATASET"
    STRATEGY = "STRATEGY"
    SDL = "SDL"
    COMPILED_STRATEGY = "COMPILED_STRATEGY"
    BACKTEST_RESULT = "BACKTEST_RESULT"
    OPTIMIZATION_RESULT = "OPTIMIZATION_RESULT"
    VALIDATION_RESULT = "VALIDATION_RESULT"
    REPLAY_RESULT = "REPLAY_RESULT"
    RESEARCH_RESULT = "RESEARCH_RESULT"
    KNOWLEDGE_RESULT = "KNOWLEDGE_RESULT"
    PORTFOLIO_RESULT = "PORTFOLIO_RESULT"
    EA_GENERATOR_RESULT = "EA_GENERATOR_RESULT"
    CLOUD_SNAPSHOT = "CLOUD_SNAPSHOT"
    WORKSPACE_SNAPSHOT = "WORKSPACE_SNAPSHOT"
    REPORT = "REPORT"
    STATISTICS = "STATISTICS"
    CONFIGURATION = "CONFIGURATION"
    DOCUMENTATION = "DOCUMENTATION"
    CUSTOM = "CUSTOM"  # reserved for future custom artifact types


class ArtifactStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"  # soft delete only -- a record is never physically removed


class ArtifactHistoryEventType(str, Enum):
    CREATED = "CREATED"
    REGISTERED = "REGISTERED"
    RENAMED = "RENAMED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    DELETED = "DELETED"
    FAVORITE_CHANGED = "FAVORITE_CHANGED"
    TAG_CHANGED = "TAG_CHANGED"
    NOTES_UPDATED = "NOTES_UPDATED"
    VERSION_INCREMENTED = "VERSION_INCREMENTED"
    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"
    REFERENCE_UPDATED = "REFERENCE_UPDATED"
    METADATA_UPDATED = "METADATA_UPDATED"
    DEPENDENCY_ADDED = "DEPENDENCY_ADDED"


class ArtifactHistoryEvent(CloudPlatformModel):
    """One immutable, checksummed entry in an artifact's append-only history.

    `checksum` covers `event_type`/`artifact_id`/`version`/`message` only
    -- `event_id` (random) and `timestamp` (wall-clock) are excluded, so
    replaying the same sequence of operations always produces the same
    sequence of event checksums.
    """

    event_id: str = Field(min_length=1)
    event_type: ArtifactHistoryEventType
    artifact_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    message: str = ""
    checksum: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactRecord(CloudPlatformModel):
    """The complete, immutable, checksummed state of one registered artifact.

    Stores ONLY metadata and references about an artifact already
    produced by another module (`source_module`) -- never the artifact's
    own content, and never a filesystem path. `dependencies` are other
    artifact ids registered in the SAME registry, forming a
    same-registry dependency graph; `references` (the reused
    `ArtifactReference` model) are checksum-only pointers to content
    outside this registry's own bookkeeping. `metadata` is a caller-
    supplied, JSON-safe dict of free-form descriptive fields -- never
    mutate it in place; every mutation on this registry replaces it
    wholesale via `update_metadata`.
    """

    artifact_id: str = Field(min_length=1)
    artifact_type: ArtifactType
    name: str = Field(min_length=1)
    description: str = ""
    workspace_id: str | None = None
    project_id: str | None = None
    source_module: str = ""
    version: int = Field(ge=1, default=1)
    checksum: str = Field(min_length=1)
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ArtifactStatus = ArtifactStatus.ACTIVE
    tags: tuple[str, ...] = Field(default_factory=tuple)
    notes: str = ""
    dependencies: tuple[str, ...] = Field(default_factory=tuple, description="Other artifact_ids registered in the same registry.")
    references: tuple[ArtifactReference, ...] = Field(default_factory=tuple, description="Checksum-only pointers to content outside this registry.")
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_favorite: bool = False
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    history: tuple[ArtifactHistoryEvent, ...] = Field(default_factory=tuple)
