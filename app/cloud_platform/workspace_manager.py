"""Offline Workspace Management orchestration (Phase 17.1).

`CloudWorkspaceManager` is the single entrypoint for every workspace/
project lifecycle operation (create, open, close, rename, archive,
restore, soft-delete, favorite, tags, notes, snapshot). It reuses --
never duplicates -- the completed Cloud Platform Foundation's
`CloudCompiler` (structural (re)compilation), `CloudValidator`
(structural validation), and `app.core.checksums.compute_checksum`
(hashing). Every mutation produces a brand-new immutable
`WorkspaceRecord` with an incremented version and an appended,
checksummed history event; nothing is ever mutated in place. 100%
offline: no authentication, no users, no networking, no database, no
file upload, no remote execution.
"""

import dataclasses
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft
from app.cloud_platform.exceptions import CloudPlatformError
from app.cloud_platform.models import ArtifactReference, CloudBuild, DatasetReference, ProjectReference, ResearchReference
from app.cloud_platform.validator import CloudValidator
from app.cloud_platform.workspace import (
    WORKSPACE_MANAGEMENT_SCHEMA_VERSION,
    ProjectRecord,
    ProjectStatus,
    WorkspaceHistoryEvent,
    WorkspaceHistoryEventType,
    WorkspaceRecord,
    WorkspaceStatus,
)
from app.cloud_platform.workspace_registry import CloudWorkspaceRegistry
from app.core.checksums import compute_checksum
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceAlreadyExistsError(CloudPlatformError):
    """Raised when creating a workspace id that's already registered."""


class ProjectAlreadyExistsError(CloudPlatformError):
    """Raised when creating a project id that already exists in its workspace."""


class ProjectNotFoundError(CloudPlatformError):
    """Raised when referencing an unknown project id within a known workspace."""


class InvalidWorkspaceStateError(CloudPlatformError):
    """Raised for an operation that is not valid given a workspace's current status."""


class InvalidProjectStateError(CloudPlatformError):
    """Raised for an operation that is not valid given a project's current status."""


class WorkspaceValidationError(CloudPlatformError):
    """Raised when a workspace mutation would fail structural validation.

    Carries the full list of `WorkspaceIssue`s for a complete report.
    """

    def __init__(self, issues: list["WorkspaceIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Workspace mutation failed validation: {summary}")


@dataclass(frozen=True)
class WorkspaceIssue:
    """One validation failure: where it occurred and why."""

    path: str
    message: str


@dataclass(frozen=True)
class WorkspaceCheckResult:
    """The outcome of validating a workspace context or a compiled `WorkspaceRecord`."""

    issues: tuple[WorkspaceIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def errors(self) -> list[WorkspaceIssue]:
        return list(self.issues)


class WorkspaceValidator:
    """Validates workspace mutations and compiled `WorkspaceRecord`s.

    Structural checks only, composed from the reused
    `app.cloud_platform.validator.CloudValidator` (duplicate ids,
    invalid/malformed references, checksum format integrity, metadata
    completeness, schema version) plus workspace-management-specific
    checks this phase adds: checksum mismatch (the record's own stored
    checksum against a recomputation), history consistency, snapshot
    consistency, and version compatibility.
    """

    def __init__(self, cloud_validator: CloudValidator | None = None) -> None:
        self._cloud_validator = cloud_validator or CloudValidator()

    def validate_context(self, context: CloudPlatformContext) -> WorkspaceCheckResult:
        """Reuses `CloudValidator` for duplicate workspace/project ids, invalid
        metadata, and invalid references."""
        result = self._cloud_validator.validate(context)
        return WorkspaceCheckResult(issues=tuple(WorkspaceIssue(i.path, i.message) for i in result.errors))

    def validate_record(self, record: WorkspaceRecord) -> WorkspaceCheckResult:
        issues: list[WorkspaceIssue] = []
        issues.extend(self._check_checksum_integrity(record))
        issues.extend(self._check_history_consistency(record))
        issues.extend(self._check_snapshot_consistency(record))
        issues.extend(self._check_version_compatibility(record))
        issues.extend(self._check_duplicate_project_records(record))
        return WorkspaceCheckResult(issues=tuple(issues))

    @staticmethod
    def _check_checksum_integrity(record: WorkspaceRecord) -> list[WorkspaceIssue]:
        recomputed = CloudWorkspaceManager._record_checksum(
            record.build, record.status, record.is_open, record.is_favorite, record.tags, record.notes, record.project_records, record.history
        )
        if recomputed != record.checksum:
            return [WorkspaceIssue("checksum", "Stored checksum does not match a recomputation of the record's own content.")]
        return []

    @staticmethod
    def _check_history_consistency(record: WorkspaceRecord) -> list[WorkspaceIssue]:
        issues: list[WorkspaceIssue] = []
        versions = [event.version for event in record.history]
        if versions != sorted(versions):
            issues.append(WorkspaceIssue("history", "History event versions are not monotonically non-decreasing."))
        if versions and versions[-1] > record.version:
            issues.append(WorkspaceIssue("history", f"Latest history event version ({versions[-1]}) exceeds the record's own version ({record.version})."))
        seen_event_ids: set[str] = set()
        for event in record.history:
            if event.event_id in seen_event_ids:
                issues.append(WorkspaceIssue("history", f"Duplicate event_id: {event.event_id!r}."))
            seen_event_ids.add(event.event_id)
        return issues

    @staticmethod
    def _check_snapshot_consistency(record: WorkspaceRecord) -> list[WorkspaceIssue]:
        known_project_ids = {project.project_id for project in record.workspace.projects}
        issues: list[WorkspaceIssue] = []
        for snapshot in record.workspace.snapshots:
            for project_id in snapshot.project_ids:
                if project_id not in known_project_ids:
                    issues.append(WorkspaceIssue("snapshots", f"Snapshot {snapshot.snapshot_id!r} references unknown project_id: {project_id!r}."))
        return issues

    @staticmethod
    def _check_version_compatibility(record: WorkspaceRecord) -> list[WorkspaceIssue]:
        if record.schema_version != WORKSPACE_MANAGEMENT_SCHEMA_VERSION:
            return [WorkspaceIssue("schema_version", f"Unsupported workspace schema version: {record.schema_version!r}.")]
        return []

    @staticmethod
    def _check_duplicate_project_records(record: WorkspaceRecord) -> list[WorkspaceIssue]:
        seen: set[str] = set()
        issues: list[WorkspaceIssue] = []
        for project_record in record.project_records:
            if project_record.project_id in seen:
                issues.append(WorkspaceIssue("project_records", f"Duplicate project_id in project_records: {project_record.project_id!r}."))
            seen.add(project_record.project_id)
        return issues


class CloudWorkspaceManager:
    """Creates and mutates local, offline research workspaces.

    Holds the caller-supplied draft state (`CloudPlatformContext`) for
    each known workspace so structural changes (rename, add project,
    snapshot) can be recompiled via the reused `CloudCompiler`, and
    delegates all storage to a `CloudWorkspaceRegistry`.
    """

    def __init__(
        self,
        registry: CloudWorkspaceRegistry | None = None,
        compiler: CloudCompiler | None = None,
        validator: CloudValidator | None = None,
    ) -> None:
        self._registry = registry or CloudWorkspaceRegistry()
        self._compiler = compiler or CloudCompiler()
        self._validator = validator or CloudValidator()
        self._contexts: dict[str, CloudPlatformContext] = {}

    @property
    def registry(self) -> CloudWorkspaceRegistry:
        return self._registry

    # -- Workspace lifecycle -------------------------------------------------

    def create_workspace(self, workspace_id: str, label: str = "") -> WorkspaceRecord:
        if self._registry.is_registered(workspace_id):
            raise WorkspaceAlreadyExistsError(f"Workspace {workspace_id!r} already exists.")

        context = CloudPlatformContext(workspace_id=workspace_id, label=label)
        self._validate_or_raise(context)
        build = self._compiler.compile(context)
        self._contexts[workspace_id] = context

        event = self._build_event(WorkspaceHistoryEventType.CREATED, workspace_id, None, version=1, message=label)
        checksum = self._record_checksum(build, WorkspaceStatus.ACTIVE, False, False, (), "", (), (event,))
        record = WorkspaceRecord(record_id=workspace_id, build=build, status=WorkspaceStatus.ACTIVE, checksum=checksum, history=(event,), version=1)
        self._registry.register(record)
        logger.info("Created workspace %s.", workspace_id)
        return record

    def open_workspace(self, workspace_id: str) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "open")
        return self._apply(workspace_id, WorkspaceHistoryEventType.OPENED, is_open=True)

    def close_workspace(self, workspace_id: str) -> WorkspaceRecord:
        self._registry.load(workspace_id)
        return self._apply(workspace_id, WorkspaceHistoryEventType.CLOSED, is_open=False)

    def rename_workspace(self, workspace_id: str, new_label: str) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "rename")
        context = self._contexts[workspace_id]
        new_context = dataclasses.replace(context, label=new_label)
        self._validate_or_raise(new_context)
        build = self._compiler.compile(new_context)
        self._contexts[workspace_id] = new_context
        return self._apply(workspace_id, WorkspaceHistoryEventType.RENAMED, message=new_label, build=build)

    def archive_workspace(self, workspace_id: str) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        if current.status != WorkspaceStatus.ACTIVE:
            raise InvalidWorkspaceStateError(f"Only an ACTIVE workspace can be archived (workspace {workspace_id!r} is {current.status.value}).")
        return self._apply(workspace_id, WorkspaceHistoryEventType.ARCHIVED, status=WorkspaceStatus.ARCHIVED, is_open=False)

    def restore_workspace(self, workspace_id: str) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        if current.status == WorkspaceStatus.ACTIVE:
            raise InvalidWorkspaceStateError(f"Workspace {workspace_id!r} is already ACTIVE.")
        return self._apply(workspace_id, WorkspaceHistoryEventType.RESTORED, status=WorkspaceStatus.ACTIVE)

    def delete_workspace(self, workspace_id: str) -> WorkspaceRecord:
        """Soft delete only -- the record and its full history are never physically removed."""
        current = self._registry.load(workspace_id)
        if current.status == WorkspaceStatus.DELETED:
            raise InvalidWorkspaceStateError(f"Workspace {workspace_id!r} is already deleted.")
        return self._apply(workspace_id, WorkspaceHistoryEventType.DELETED, status=WorkspaceStatus.DELETED, is_open=False)

    def favorite_workspace(self, workspace_id: str, favorite: bool = True) -> WorkspaceRecord:
        self._registry.load(workspace_id)
        return self._apply(workspace_id, WorkspaceHistoryEventType.FAVORITE_CHANGED, is_favorite=favorite, message=str(favorite))

    def set_workspace_tags(self, workspace_id: str, tags: tuple[str, ...]) -> WorkspaceRecord:
        self._registry.load(workspace_id)
        return self._apply(workspace_id, WorkspaceHistoryEventType.TAG_CHANGED, tags=tuple(tags))

    def set_workspace_notes(self, workspace_id: str, notes: str) -> WorkspaceRecord:
        self._registry.load(workspace_id)
        return self._apply(workspace_id, WorkspaceHistoryEventType.METADATA_UPDATED, notes=notes)

    def snapshot_workspace(self, workspace_id: str, label: str = "") -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "snapshot")
        context = self._contexts[workspace_id]
        project_ids = tuple(draft.project_id for draft in context.projects)
        # Deterministic, not a random uuid4 -- snapshot_id is part of the
        # compiled CloudSnapshot's checksummed payload, so randomness here
        # would silently break cross-run determinism of the whole workspace.
        snapshot_id = f"{workspace_id}-snapshot-{len(context.snapshots) + 1}"
        new_snapshot = SnapshotDraft(snapshot_id=snapshot_id, label=label, project_ids=project_ids)
        new_context = dataclasses.replace(context, snapshots=context.snapshots + (new_snapshot,))
        self._validate_or_raise(new_context)
        build = self._compiler.compile(new_context)
        self._contexts[workspace_id] = new_context
        return self._apply(workspace_id, WorkspaceHistoryEventType.SNAPSHOT_TAKEN, message=new_snapshot.snapshot_id, build=build)

    def add_project_reference(self, workspace_id: str, reference: ProjectReference) -> WorkspaceRecord:
        """Cross-references another workspace's project, by id/checksum only."""
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "add a project reference to")
        context = self._contexts[workspace_id]
        new_context = dataclasses.replace(context, project_references=context.project_references + (reference,))
        self._validate_or_raise(new_context)
        build = self._compiler.compile(new_context)
        self._contexts[workspace_id] = new_context
        return self._apply(workspace_id, WorkspaceHistoryEventType.METADATA_UPDATED, message=reference.reference_id, build=build)

    # -- Project lifecycle -----------------------------------------------------

    def create_project(
        self,
        workspace_id: str,
        project_id: str,
        name: str,
        research_references: tuple[ResearchReference, ...] = (),
        dataset_references: tuple[DatasetReference, ...] = (),
        artifact_references: tuple[ArtifactReference, ...] = (),
    ) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "add a project to")
        context = self._contexts[workspace_id]
        if any(draft.project_id == project_id for draft in context.projects):
            raise ProjectAlreadyExistsError(f"Project {project_id!r} already exists in workspace {workspace_id!r}.")

        draft = ProjectDraft(
            project_id=project_id,
            name=name,
            research_references=research_references,
            dataset_references=dataset_references,
            artifact_references=artifact_references,
        )
        new_context = dataclasses.replace(context, projects=context.projects + (draft,))
        self._validate_or_raise(new_context)
        build = self._compiler.compile(new_context)
        self._contexts[workspace_id] = new_context

        checksum = self._project_record_checksum(project_id, ProjectStatus.ACTIVE, False, (), "")
        new_project_record = ProjectRecord(project_id=project_id, checksum=checksum)
        new_project_records = current.project_records + (new_project_record,)
        return self._apply(
            workspace_id, WorkspaceHistoryEventType.PROJECT_CREATED, project_id=project_id, message=name, build=build, project_records=new_project_records
        )

    def rename_project(self, workspace_id: str, project_id: str, new_name: str) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "rename a project in")
        context = self._contexts[workspace_id]
        drafts = list(context.projects)
        for index, draft in enumerate(drafts):
            if draft.project_id == project_id:
                drafts[index] = dataclasses.replace(draft, name=new_name)
                break
        else:
            raise ProjectNotFoundError(f"Unknown project {project_id!r} in workspace {workspace_id!r}.")

        new_context = dataclasses.replace(context, projects=tuple(drafts))
        self._validate_or_raise(new_context)
        build = self._compiler.compile(new_context)
        self._contexts[workspace_id] = new_context
        return self._apply(workspace_id, WorkspaceHistoryEventType.PROJECT_RENAMED, project_id=project_id, message=new_name, build=build)

    def archive_project(self, workspace_id: str, project_id: str) -> WorkspaceRecord:
        existing = self._require_project_record(workspace_id, project_id)
        if existing.status != ProjectStatus.ACTIVE:
            raise InvalidProjectStateError(f"Only an ACTIVE project can be archived (project {project_id!r} is {existing.status.value}).")
        return self._update_project_record(workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_ARCHIVED, status=ProjectStatus.ARCHIVED)

    def restore_project(self, workspace_id: str, project_id: str) -> WorkspaceRecord:
        existing = self._require_project_record(workspace_id, project_id)
        if existing.status == ProjectStatus.ACTIVE:
            raise InvalidProjectStateError(f"Project {project_id!r} is already ACTIVE.")
        return self._update_project_record(workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_RESTORED, status=ProjectStatus.ACTIVE)

    def delete_project(self, workspace_id: str, project_id: str) -> WorkspaceRecord:
        """Soft delete only -- the project record is never physically removed."""
        existing = self._require_project_record(workspace_id, project_id)
        if existing.status == ProjectStatus.DELETED:
            raise InvalidProjectStateError(f"Project {project_id!r} is already deleted.")
        return self._update_project_record(workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_DELETED, status=ProjectStatus.DELETED)

    def favorite_project(self, workspace_id: str, project_id: str, favorite: bool = True) -> WorkspaceRecord:
        self._require_project_record(workspace_id, project_id)
        return self._update_project_record(
            workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_FAVORITE_CHANGED, is_favorite=favorite, message=str(favorite)
        )

    def set_project_tags(self, workspace_id: str, project_id: str, tags: tuple[str, ...]) -> WorkspaceRecord:
        self._require_project_record(workspace_id, project_id)
        return self._update_project_record(workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_TAG_CHANGED, tags=tuple(tags))

    def set_project_notes(self, workspace_id: str, project_id: str, notes: str) -> WorkspaceRecord:
        self._require_project_record(workspace_id, project_id)
        return self._update_project_record(workspace_id, project_id, WorkspaceHistoryEventType.PROJECT_METADATA_UPDATED, notes=notes)

    # -- Read access -------------------------------------------------------

    def get_workspace(self, workspace_id: str) -> WorkspaceRecord:
        return self._registry.load(workspace_id)

    def list_workspaces(self, include_disabled: bool = True) -> list[WorkspaceRecord]:
        return self._registry.list(include_disabled=include_disabled)

    def version_history(self, workspace_id: str) -> list[WorkspaceRecord]:
        return self._registry.version_history(workspace_id)

    # -- Internal helpers ----------------------------------------------------

    def _require_project_record(self, workspace_id: str, project_id: str) -> ProjectRecord:
        current = self._registry.load(workspace_id)
        self._guard_not_deleted(current, "update a project in")
        existing = current.project_record(project_id)
        if existing is None:
            raise ProjectNotFoundError(f"Unknown project {project_id!r} in workspace {workspace_id!r}.")
        return existing

    def _update_project_record(self, workspace_id: str, project_id: str, event_type: WorkspaceHistoryEventType, **changes) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        existing = current.project_record(project_id)
        assert existing is not None  # guaranteed by callers via _require_project_record
        status = changes.get("status", existing.status)
        is_favorite = changes.get("is_favorite", existing.is_favorite)
        tags = changes.get("tags", existing.tags)
        notes = changes.get("notes", existing.notes)
        checksum = self._project_record_checksum(project_id, status, is_favorite, tags, notes)
        updated = ProjectRecord(
            project_id=project_id,
            status=status,
            is_favorite=is_favorite,
            tags=tags,
            notes=notes,
            version=existing.version + 1,
            checksum=checksum,
            created_at=existing.created_at,
        )
        new_project_records = tuple(updated if record.project_id == project_id else record for record in current.project_records)
        message = str(changes.get("message", ""))
        return self._apply(workspace_id, event_type, project_id=project_id, message=message, project_records=new_project_records)

    @staticmethod
    def _guard_not_deleted(record: WorkspaceRecord, action: str) -> None:
        if record.status == WorkspaceStatus.DELETED:
            raise InvalidWorkspaceStateError(f"Cannot {action} a deleted workspace {record.workspace.workspace_id!r}.")

    def _validate_or_raise(self, context: CloudPlatformContext) -> None:
        result = self._validator.validate(context)
        if not result.is_valid:
            raise WorkspaceValidationError([WorkspaceIssue(issue.path, issue.message) for issue in result.errors])

    def _apply(
        self,
        workspace_id: str,
        event_type: WorkspaceHistoryEventType,
        *,
        project_id: str | None = None,
        message: str = "",
        build: CloudBuild | None = None,
        status: WorkspaceStatus | None = None,
        is_open: bool | None = None,
        is_favorite: bool | None = None,
        tags: tuple[str, ...] | None = None,
        notes: str | None = None,
        project_records: tuple[ProjectRecord, ...] | None = None,
    ) -> WorkspaceRecord:
        current = self._registry.load(workspace_id)
        new_build = build if build is not None else current.build
        new_status = status if status is not None else current.status
        new_is_open = is_open if is_open is not None else current.is_open
        new_is_favorite = is_favorite if is_favorite is not None else current.is_favorite
        new_tags = tags if tags is not None else current.tags
        new_notes = notes if notes is not None else current.notes
        new_project_records = project_records if project_records is not None else current.project_records
        new_version = current.version + 1

        event = self._build_event(event_type, workspace_id, project_id, version=new_version, message=message)
        new_history = current.history + (event,)

        checksum = self._record_checksum(new_build, new_status, new_is_open, new_is_favorite, new_tags, new_notes, new_project_records, new_history)

        record = WorkspaceRecord(
            record_id=workspace_id,
            build=new_build,
            status=new_status,
            is_open=new_is_open,
            is_favorite=new_is_favorite,
            tags=new_tags,
            notes=new_notes,
            project_records=new_project_records,
            history=new_history,
            version=new_version,
            checksum=checksum,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._registry.register(record)
        return record

    @staticmethod
    def _build_event(event_type: WorkspaceHistoryEventType, workspace_id: str, project_id: str | None, version: int, message: str) -> WorkspaceHistoryEvent:
        checksum = CloudWorkspaceManager._event_checksum(event_type, workspace_id, project_id, version, message)
        return WorkspaceHistoryEvent(
            event_id=str(uuid.uuid4()), event_type=event_type, workspace_id=workspace_id, project_id=project_id, version=version, message=message, checksum=checksum
        )

    @staticmethod
    def _event_checksum(event_type: WorkspaceHistoryEventType, workspace_id: str, project_id: str | None, version: int, message: str) -> str:
        payload = {"event_type": event_type.value, "workspace_id": workspace_id, "project_id": project_id, "version": version, "message": message}
        return compute_checksum(payload)

    @staticmethod
    def _project_record_checksum(project_id: str, status: ProjectStatus, is_favorite: bool, tags: tuple[str, ...], notes: str) -> str:
        payload = {"project_id": project_id, "status": status.value, "is_favorite": is_favorite, "tags": sorted(tags), "notes": notes}
        return compute_checksum(payload)

    @staticmethod
    def _record_checksum(
        build: CloudBuild,
        status: WorkspaceStatus,
        is_open: bool,
        is_favorite: bool,
        tags: tuple[str, ...],
        notes: str,
        project_records: tuple[ProjectRecord, ...],
        history: tuple[WorkspaceHistoryEvent, ...],
    ) -> str:
        payload = {
            "build_checksum": build.checksum,
            "status": status.value,
            "is_open": is_open,
            "is_favorite": is_favorite,
            "tags": sorted(tags),
            "notes": notes,
            "project_records": [pr.model_dump(mode="json", exclude={"created_at", "updated_at"}) for pr in project_records],
            "history": [event.model_dump(mode="json", exclude={"event_id", "timestamp"}) for event in history],
        }
        return compute_checksum(payload)
