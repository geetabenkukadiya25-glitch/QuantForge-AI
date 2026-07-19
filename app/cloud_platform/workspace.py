"""Immutable data models for offline Cloud Workspace Management (Phase 17.1).

Wraps -- never duplicates or modifies -- the completed Cloud Platform
Foundation's `CloudWorkspace`/`CloudProject`/`CloudBuild` models
(`app.cloud_platform.models`) with the lifecycle state those foundation
models intentionally do not carry: status (active/archived/soft-deleted),
open/closed, favorites, tags, notes, and an append-only, checksummed
history. Everything here is offline: no authentication, no users, no
networking, no database, no file upload.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import Field

from app.cloud_platform.models import CloudBuild, CloudPlatformModel, CloudWorkspace

WORKSPACE_MANAGEMENT_SCHEMA_VERSION = "1.0.0"


class WorkspaceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"  # soft delete only -- a record is never physically removed


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"  # soft delete only -- a record is never physically removed


class WorkspaceHistoryEventType(str, Enum):
    CREATED = "CREATED"
    OPENED = "OPENED"
    CLOSED = "CLOSED"
    RENAMED = "RENAMED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    DELETED = "DELETED"
    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"
    METADATA_UPDATED = "METADATA_UPDATED"
    TAG_CHANGED = "TAG_CHANGED"
    FAVORITE_CHANGED = "FAVORITE_CHANGED"
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_RENAMED = "PROJECT_RENAMED"
    PROJECT_ARCHIVED = "PROJECT_ARCHIVED"
    PROJECT_RESTORED = "PROJECT_RESTORED"
    PROJECT_DELETED = "PROJECT_DELETED"
    PROJECT_METADATA_UPDATED = "PROJECT_METADATA_UPDATED"
    PROJECT_TAG_CHANGED = "PROJECT_TAG_CHANGED"
    PROJECT_FAVORITE_CHANGED = "PROJECT_FAVORITE_CHANGED"


class WorkspaceHistoryEvent(CloudPlatformModel):
    """One immutable, checksummed entry in a workspace's append-only history.

    `checksum` covers `event_type`/`workspace_id`/`project_id`/`version`/
    `message` only -- `event_id` (random) and `timestamp` (wall-clock) are
    excluded, so replaying the same sequence of operations always
    produces the same sequence of event checksums.
    """

    event_id: str = Field(min_length=1)
    event_type: WorkspaceHistoryEventType
    workspace_id: str = Field(min_length=1)
    project_id: str | None = None
    version: int = Field(ge=1)
    message: str = ""
    checksum: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectRecord(CloudPlatformModel):
    """Lifecycle wrapper around one project id: status, favorite, tags, notes.

    Deliberately holds NO project content of its own (name/references) --
    that stays exclusively on the reused, immutable `CloudProject` inside
    `CloudWorkspace.projects`. This is metadata-only bookkeeping,
    keyed by `project_id`.
    """

    project_id: str = Field(min_length=1)
    status: ProjectStatus = ProjectStatus.ACTIVE
    is_favorite: bool = False
    tags: tuple[str, ...] = Field(default_factory=tuple)
    notes: str = ""
    version: int = Field(ge=1, default=1)
    checksum: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceRecord(CloudPlatformModel):
    """The complete, immutable, checksummed lifecycle state of one workspace.

    Wraps a reused, unmodified `CloudBuild` (the compiled `CloudWorkspace`'s
    project/snapshot/reference content, produced by
    `app.cloud_platform.compiler.CloudCompiler`) with the offline
    workspace-management state this phase adds: status, open/closed,
    favorite, tags, notes, per-project lifecycle records, and an
    append-only, checksummed history. `workspace` is a plain accessor
    over `build.workspace` -- it adds no duplicate data to serialization.
    """

    record_id: str = Field(min_length=1)
    build: CloudBuild
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    is_open: bool = False
    is_favorite: bool = False
    tags: tuple[str, ...] = Field(default_factory=tuple)
    notes: str = ""
    project_records: tuple[ProjectRecord, ...] = Field(default_factory=tuple)
    history: tuple[WorkspaceHistoryEvent, ...] = Field(default_factory=tuple)
    schema_version: str = WORKSPACE_MANAGEMENT_SCHEMA_VERSION
    version: int = Field(ge=1, default=1)
    checksum: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def workspace(self) -> CloudWorkspace:
        return self.build.workspace

    def project_record(self, project_id: str) -> ProjectRecord | None:
        for record in self.project_records:
            if record.project_id == project_id:
                return record
        return None
