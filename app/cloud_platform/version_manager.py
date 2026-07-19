"""Offline Project Versioning & Snapshot System orchestration (Phase 17.3).

`CloudVersionManager` is the single entrypoint for every version
lifecycle operation (create, snapshot, restore, compare, archive,
restore status, soft-delete, favorite, tags, notes, metadata/reference
update). This is NOT Git and NOT source-code versioning -- it is an
internal, deterministic version-history layer over objects already
managed elsewhere (workspaces, artifacts, and any future object type).
It never inspects a versioned subject's actual content -- only a
caller-supplied `snapshot_checksum` identifying it. Every mutation
produces a brand-new immutable `VersionRecord` with an appended,
checksummed history event; nothing is ever mutated in place. Reuses --
never duplicates -- `app.core.checksums.compute_checksum` and the same
lifecycle-record discipline `app.cloud_platform.workspace_manager`/
`app.cloud_platform.artifact_manager` established. Optionally composes
`app.cloud_platform.artifact_registry.CloudArtifactRegistry` (reused,
never modified) to resolve dependency comparisons for ARTIFACT-typed
subjects. 100% offline: no authentication, no users, no networking, no
database, no workers, no broker/MetaTrader/execution-engine code.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from app.cloud_platform.artifact_registry import CloudArtifactRegistry
from app.cloud_platform.exceptions import CloudPlatformError
from app.cloud_platform.version_registry import CloudVersionRegistry
from app.cloud_platform.versioning import (
    VERSION_SCHEMA_VERSION,
    VersionComparison,
    VersionHistory,
    VersionHistoryEventType,
    VersionReference,
    VersionRecord,
    VersionSnapshot,
    VersionStatus,
    VersionSubjectType,
)
from app.core.checksums import compute_checksum
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class InvalidVersionStateError(CloudPlatformError):
    """Raised for an operation that is not valid given a version's current status."""


class SubjectMismatchError(CloudPlatformError):
    """Raised when a version doesn't belong to the expected subject lineage."""


class VersionValidationError(CloudPlatformError):
    """Raised when a version mutation would fail structural validation.

    Carries the full list of `VersionIssue`s for a complete report.
    """

    def __init__(self, issues: list["VersionIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Version mutation failed validation: {summary}")


@dataclass(frozen=True)
class VersionIssue:
    """One validation failure: where it occurred and why."""

    path: str
    message: str


@dataclass(frozen=True)
class VersionCheckResult:
    """The outcome of validating a new version, a compiled `VersionRecord`, or a registry."""

    issues: tuple[VersionIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def errors(self) -> list[VersionIssue]:
        return list(self.issues)


class VersionValidator:
    """Validates version creation, compiled `VersionRecord`s, and registries.

    Structural checks only: duplicate versions, broken parent chains,
    invalid version numbers, checksum mismatch, snapshot mismatch,
    history mismatch, reference mismatch, and metadata errors. No
    business logic about what a "good" version looks like.
    """

    def validate_new(
        self,
        version_id: str,
        subject_type: VersionSubjectType,
        subject_id: str,
        parent_version: str | None,
        references: tuple[VersionReference, ...],
        registry: CloudVersionRegistry,
    ) -> VersionCheckResult:
        issues: list[VersionIssue] = []
        if not version_id or not version_id.strip():
            issues.append(VersionIssue("version_id", "version_id must be non-empty."))
        elif registry.is_registered(version_id):
            issues.append(VersionIssue("version_id", f"Duplicate version_id: {version_id!r}."))
        if not subject_id or not subject_id.strip():
            issues.append(VersionIssue("subject_id", "subject_id must be non-empty."))
        if parent_version is not None:
            if not registry.is_registered(parent_version):
                issues.append(VersionIssue("parent_version", f"Broken parent chain: unknown version_id {parent_version!r}."))
            else:
                parent = registry.load(parent_version)
                if parent.subject_type != subject_type or parent.subject_id != subject_id:
                    issues.append(VersionIssue("parent_version", f"parent_version {parent_version!r} belongs to a different subject."))
        issues.extend(self._check_references(references, registry))
        return VersionCheckResult(issues=tuple(issues))

    def validate_record(self, record: VersionRecord, registry: CloudVersionRegistry | None = None) -> VersionCheckResult:
        issues: list[VersionIssue] = []
        issues.extend(self._check_checksum_integrity(record))
        issues.extend(self._check_history_consistency(record))
        issues.extend(self._check_version_number(record))
        issues.extend(self._check_metadata(record))
        issues.extend(self._check_references(record.references, registry))
        if registry is not None:
            issues.extend(self._check_parent_chain(record, registry))
            issues.extend(self._check_snapshot_consistency(record, registry))
        return VersionCheckResult(issues=tuple(issues))

    def validate_registry(self, records: list[VersionRecord]) -> VersionCheckResult:
        """Registry-wide check: duplicate (subject_type, subject_id, version_number)
        triples shared by two currently non-deleted versions."""
        issues: list[VersionIssue] = []
        seen: dict[tuple, str] = {}
        for record in records:
            if record.status == VersionStatus.DELETED:
                continue
            key = (record.subject_type, record.subject_id, record.version_number)
            if key in seen:
                issues.append(
                    VersionIssue(
                        "version_number",
                        f"Duplicate version_number {record.version_number} for "
                        f"{record.subject_type.value}:{record.subject_id!r} shared by {seen[key]!r} and {record.version_id!r}.",
                    )
                )
            else:
                seen[key] = record.version_id
        return VersionCheckResult(issues=tuple(issues))

    @staticmethod
    def _check_references(references: tuple[VersionReference, ...], registry: CloudVersionRegistry | None = None) -> list[VersionIssue]:
        issues: list[VersionIssue] = []
        for reference in references:
            if not _SHA256_HEX_RE.match(reference.checksum):
                issues.append(VersionIssue("references", f"Malformed checksum for reference {reference.reference_id!r}."))
            if registry is not None and not registry.is_registered(reference.version_id):
                issues.append(VersionIssue("references", f"Reference mismatch: unknown version_id {reference.version_id!r}."))
        return issues

    @staticmethod
    def _check_checksum_integrity(record: VersionRecord) -> list[VersionIssue]:
        recomputed = CloudVersionManager._record_checksum(
            record.subject_type,
            record.subject_id,
            record.parent_version,
            record.version_number,
            record.snapshot_checksum,
            record.workspace_id,
            record.project_id,
            record.artifact_id,
            record.change_summary,
            record.author,
            record.status,
            record.is_favorite,
            record.tags,
            record.notes,
            record.metadata,
            record.references,
            record.history,
        )
        if recomputed != record.checksum:
            return [VersionIssue("checksum", "Stored checksum does not match a recomputation of the record's own content.")]
        return []

    @staticmethod
    def _check_history_consistency(record: VersionRecord) -> list[VersionIssue]:
        issues: list[VersionIssue] = []
        seen_event_ids: set[str] = set()
        for event in record.history:
            if event.event_id in seen_event_ids:
                issues.append(VersionIssue("history", f"Duplicate event_id: {event.event_id!r}."))
            seen_event_ids.add(event.event_id)
        return issues

    @staticmethod
    def _check_version_number(record: VersionRecord) -> list[VersionIssue]:
        issues: list[VersionIssue] = []
        if record.version_number < 1:
            issues.append(VersionIssue("version_number", "version_number must be >= 1."))
        if record.schema_version != VERSION_SCHEMA_VERSION:
            issues.append(VersionIssue("schema_version", f"Unsupported version schema version: {record.schema_version!r}."))
        return issues

    @staticmethod
    def _check_metadata(record: VersionRecord) -> list[VersionIssue]:
        issues: list[VersionIssue] = []
        for key in record.metadata:
            if not isinstance(key, str) or not key:
                issues.append(VersionIssue("metadata", f"Metadata keys must be non-empty strings, got {key!r}."))
        return issues

    @staticmethod
    def _check_parent_chain(record: VersionRecord, registry: CloudVersionRegistry) -> list[VersionIssue]:
        if record.parent_version is None:
            return []
        if not registry.is_registered(record.parent_version):
            return [VersionIssue("parent_version", f"Broken parent chain: unknown version_id {record.parent_version!r}.")]
        parent = registry.load(record.parent_version)
        issues: list[VersionIssue] = []
        if parent.subject_type != record.subject_type or parent.subject_id != record.subject_id:
            issues.append(VersionIssue("parent_version", f"parent_version {record.parent_version!r} belongs to a different subject."))
        if parent.version_number >= record.version_number:
            issues.append(VersionIssue("version_number", f"version_number ({record.version_number}) must exceed its parent's ({parent.version_number})."))
        return issues

    @staticmethod
    def _check_snapshot_consistency(record: VersionRecord, registry: CloudVersionRegistry) -> list[VersionIssue]:
        issues: list[VersionIssue] = []
        for snapshot in registry.snapshots_of(record.version_id):
            if snapshot.snapshot_checksum != record.snapshot_checksum:
                issues.append(VersionIssue("snapshot_checksum", f"Snapshot {snapshot.snapshot_id!r} checksum does not match the version's own snapshot_checksum."))
        return issues


class CloudVersionManager:
    """Creates and mutates local, offline version records for any versioned subject."""

    def __init__(
        self,
        registry: CloudVersionRegistry | None = None,
        validator: VersionValidator | None = None,
        artifact_registry: CloudArtifactRegistry | None = None,
    ) -> None:
        self._registry = registry or CloudVersionRegistry()
        self._validator = validator or VersionValidator()
        self._artifact_registry = artifact_registry

    @property
    def registry(self) -> CloudVersionRegistry:
        return self._registry

    # -- Create ---------------------------------------------------------------

    def create_version(
        self,
        version_id: str,
        subject_type: VersionSubjectType,
        subject_id: str,
        snapshot_checksum: str,
        parent_version: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        artifact_id: str | None = None,
        change_summary: str = "",
        author: str = "",
        metadata: dict[str, Any] | None = None,
        references: tuple[VersionReference, ...] = (),
        tags: tuple[str, ...] = (),
        notes: str = "",
    ) -> VersionRecord:
        metadata = dict(metadata or {})
        references = tuple(references)
        tags = tuple(tags)

        check = self._validator.validate_new(version_id, subject_type, subject_id, parent_version, references, self._registry)
        if not check.is_valid:
            raise VersionValidationError([VersionIssue(issue.path, issue.message) for issue in check.errors])

        existing = self._registry.list_by_subject(subject_type, subject_id)
        version_number = max((version.version_number for version in existing), default=0) + 1

        event = self._build_event(VersionHistoryEventType.CREATED, version_id, message=change_summary)
        checksum = self._record_checksum(
            subject_type, subject_id, parent_version, version_number, snapshot_checksum, workspace_id, project_id, artifact_id,
            change_summary, author, VersionStatus.ACTIVE, False, tags, notes, metadata, references, (event,),
        )
        record = VersionRecord(
            version_id=version_id,
            subject_type=subject_type,
            subject_id=subject_id,
            parent_version=parent_version,
            version_number=version_number,
            checksum=checksum,
            snapshot_checksum=snapshot_checksum,
            workspace_id=workspace_id,
            project_id=project_id,
            artifact_id=artifact_id,
            change_summary=change_summary,
            author=author,
            status=VersionStatus.ACTIVE,
            metadata=metadata,
            references=references,
            history=(event,),
            tags=tags,
            notes=notes,
            is_favorite=False,
        )
        self._registry.register(record)
        logger.info("Created version %s for %s:%s (v%d).", version_id, subject_type.value, subject_id, version_number)
        return record

    # -- Snapshot / Restore ----------------------------------------------------

    def snapshot(self, version_id: str, label: str = "") -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "snapshot")
        snapshot_id = f"{version_id}-snapshot-{len(self._registry.snapshots_of(version_id)) + 1}"
        record_snapshot = VersionSnapshot(
            snapshot_id=snapshot_id,
            version_id=version_id,
            subject_type=current.subject_type,
            subject_id=current.subject_id,
            snapshot_checksum=current.snapshot_checksum,
            label=label,
        )
        self._registry.register_snapshot(record_snapshot)
        return self._apply(version_id, VersionHistoryEventType.SNAPSHOT_TAKEN, message=snapshot_id)

    def restore_snapshot(
        self, subject_type: VersionSubjectType, subject_id: str, target_version_id: str, new_version_id: str, change_summary: str = ""
    ) -> VersionRecord:
        """Create a brand-new version for `subject_type`/`subject_id` whose
        content identity (`snapshot_checksum`) matches `target_version_id`'s
        -- restoring by creating a new version, never by mutating an old one."""
        target = self._registry.load(target_version_id)
        if target.subject_type != subject_type or target.subject_id != subject_id:
            raise SubjectMismatchError(f"Version {target_version_id!r} does not belong to {subject_type.value}:{subject_id!r}.")

        latest = self.latest_version(subject_type, subject_id)
        parent_version = latest.version_id if latest is not None else None
        summary = change_summary or f"Restored from version {target_version_id!r}."

        record = self.create_version(
            version_id=new_version_id,
            subject_type=subject_type,
            subject_id=subject_id,
            snapshot_checksum=target.snapshot_checksum,
            parent_version=parent_version,
            workspace_id=target.workspace_id,
            project_id=target.project_id,
            artifact_id=target.artifact_id,
            change_summary=summary,
            author=target.author,
            metadata=dict(target.metadata),
            references=target.references,
        )
        return self._apply(record.version_id, VersionHistoryEventType.RESTORED, message=target_version_id)

    # -- Comparison ------------------------------------------------------------

    def compare_versions(self, version_id_a: str, version_id_b: str) -> VersionComparison:
        version_a = self._registry.load(version_id_a)
        version_b = self._registry.load(version_id_b)

        checksum_equal = version_a.checksum == version_b.checksum
        snapshot_checksum_equal = version_a.snapshot_checksum == version_b.snapshot_checksum
        metadata_equal = version_a.metadata == version_b.metadata
        references_equal = {r.checksum for r in version_a.references} == {r.checksum for r in version_b.references}
        history_equal = [e.checksum for e in version_a.history] == [e.checksum for e in version_b.history]
        dependencies_equal = self._compare_dependencies(version_a, version_b)

        differences: list[str] = []
        if not checksum_equal:
            differences.append("checksum")
        if not snapshot_checksum_equal:
            differences.append("snapshot_checksum")
        if not metadata_equal:
            differences.append("metadata")
        if not references_equal:
            differences.append("references")
        if not history_equal:
            differences.append("history")
        if dependencies_equal is False:
            differences.append("dependencies")
        if version_a.version_number != version_b.version_number:
            differences.append("version_number")
        if version_a.created_time != version_b.created_time:
            differences.append("created_time")

        return VersionComparison(
            comparison_id=f"{version_id_a}:{version_id_b}",
            version_id_a=version_id_a,
            version_id_b=version_id_b,
            checksum_equal=checksum_equal,
            snapshot_checksum_equal=snapshot_checksum_equal,
            metadata_equal=metadata_equal,
            references_equal=references_equal,
            history_equal=history_equal,
            dependencies_equal=dependencies_equal,
            version_number_delta=version_b.version_number - version_a.version_number,
            created_time_delta_seconds=(version_b.created_time - version_a.created_time).total_seconds(),
            differences=tuple(differences),
        )

    def _compare_dependencies(self, version_a: VersionRecord, version_b: VersionRecord) -> bool | None:
        if self._artifact_registry is None:
            return None
        if version_a.subject_type != VersionSubjectType.ARTIFACT or version_b.subject_type != VersionSubjectType.ARTIFACT:
            return None
        dependencies_a = self._resolve_artifact_dependencies(version_a)
        dependencies_b = self._resolve_artifact_dependencies(version_b)
        if dependencies_a is None or dependencies_b is None:
            return None
        return set(dependencies_a) == set(dependencies_b)

    def _resolve_artifact_dependencies(self, version: VersionRecord) -> tuple[str, ...] | None:
        if version.artifact_id is None or self._artifact_registry is None:
            return None
        if not self._artifact_registry.is_registered(version.artifact_id):
            return None
        for artifact_record in self._artifact_registry.version_history(version.artifact_id):
            if artifact_record.checksum == version.snapshot_checksum:
                return artifact_record.dependencies
        return None

    # -- Navigation --------------------------------------------------------

    def latest_version(self, subject_type: VersionSubjectType, subject_id: str) -> VersionRecord | None:
        versions = self._registry.list_by_subject(subject_type, subject_id)
        return versions[-1] if versions else None

    def previous_version(self, version_id: str) -> VersionRecord | None:
        current = self._registry.load(version_id)
        if current.parent_version is None:
            return None
        return self._registry.load(current.parent_version)

    def next_versions(self, version_id: str) -> list[VersionRecord]:
        return self._registry.children_of(version_id)

    def version_tree(self, subject_type: VersionSubjectType, subject_id: str) -> dict[str, tuple[str, ...]]:
        return self._registry.tree_of(subject_type, subject_id)

    def version_timeline(self, subject_type: VersionSubjectType, subject_id: str) -> list[VersionRecord]:
        return self._registry.list_by_subject(subject_type, subject_id)

    # -- Lifecycle ------------------------------------------------------------

    def set_version_notes(self, version_id: str, notes: str) -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "update notes on")
        return self._apply(version_id, VersionHistoryEventType.NOTES_UPDATED, notes=notes)

    def set_version_tags(self, version_id: str, tags: tuple[str, ...]) -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "update tags on")
        return self._apply(version_id, VersionHistoryEventType.TAG_CHANGED, tags=tuple(tags))

    def favorite_version(self, version_id: str, favorite: bool = True) -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "favorite")
        return self._apply(version_id, VersionHistoryEventType.FAVORITE_CHANGED, is_favorite=favorite, message=str(favorite))

    def archive_version(self, version_id: str) -> VersionRecord:
        current = self._registry.load(version_id)
        if current.status != VersionStatus.ACTIVE:
            raise InvalidVersionStateError(f"Only an ACTIVE version can be archived (version {version_id!r} is {current.status.value}).")
        return self._apply(version_id, VersionHistoryEventType.ARCHIVED, status=VersionStatus.ARCHIVED)

    def restore_version_status(self, version_id: str) -> VersionRecord:
        current = self._registry.load(version_id)
        if current.status == VersionStatus.ACTIVE:
            raise InvalidVersionStateError(f"Version {version_id!r} is already ACTIVE.")
        return self._apply(version_id, VersionHistoryEventType.RESTORED_STATUS, status=VersionStatus.ACTIVE)

    def delete_version(self, version_id: str) -> VersionRecord:
        """Soft delete only -- the record and its full history are never physically removed."""
        current = self._registry.load(version_id)
        if current.status == VersionStatus.DELETED:
            raise InvalidVersionStateError(f"Version {version_id!r} is already deleted.")
        return self._apply(version_id, VersionHistoryEventType.DELETED, status=VersionStatus.DELETED)

    def update_metadata(self, version_id: str, metadata: dict[str, Any]) -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "update metadata on")
        return self._apply(version_id, VersionHistoryEventType.METADATA_UPDATED, metadata=dict(metadata))

    def update_references(self, version_id: str, references: tuple[VersionReference, ...]) -> VersionRecord:
        current = self._registry.load(version_id)
        self._guard_not_deleted(current, "update references on")
        references = tuple(references)
        issues = self._validator._check_references(references, self._registry)
        if issues:
            raise VersionValidationError(issues)
        return self._apply(version_id, VersionHistoryEventType.REFERENCE_UPDATED, references=references)

    # -- Read access -------------------------------------------------------

    def get_version(self, version_id: str) -> VersionRecord:
        return self._registry.load(version_id)

    def list_versions(self, include_disabled: bool = True) -> list[VersionRecord]:
        return self._registry.list(include_disabled=include_disabled)

    def version_history(self, version_id: str) -> list[VersionRecord]:
        return self._registry.version_history(version_id)

    # -- Internal helpers ----------------------------------------------------

    @staticmethod
    def _guard_not_deleted(record: VersionRecord, action: str) -> None:
        if record.status == VersionStatus.DELETED:
            raise InvalidVersionStateError(f"Cannot {action} a deleted version {record.version_id!r}.")

    def _apply(
        self,
        version_id: str,
        event_type: VersionHistoryEventType,
        *,
        message: str = "",
        status: VersionStatus | None = None,
        is_favorite: bool | None = None,
        tags: tuple[str, ...] | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
        references: tuple[VersionReference, ...] | None = None,
    ) -> VersionRecord:
        current = self._registry.load(version_id)
        new_status = status if status is not None else current.status
        new_is_favorite = is_favorite if is_favorite is not None else current.is_favorite
        new_tags = tags if tags is not None else current.tags
        new_notes = notes if notes is not None else current.notes
        new_metadata = metadata if metadata is not None else current.metadata
        new_references = references if references is not None else current.references

        event = self._build_event(event_type, version_id, message=message)
        new_history = current.history + (event,)

        checksum = self._record_checksum(
            current.subject_type, current.subject_id, current.parent_version, current.version_number, current.snapshot_checksum,
            current.workspace_id, current.project_id, current.artifact_id, current.change_summary, current.author,
            new_status, new_is_favorite, new_tags, new_notes, new_metadata, new_references, new_history,
        )

        record = VersionRecord(
            version_id=version_id,
            subject_type=current.subject_type,
            subject_id=current.subject_id,
            parent_version=current.parent_version,
            version_number=current.version_number,
            created_time=current.created_time,
            checksum=checksum,
            snapshot_checksum=current.snapshot_checksum,
            workspace_id=current.workspace_id,
            project_id=current.project_id,
            artifact_id=current.artifact_id,
            change_summary=current.change_summary,
            author=current.author,
            status=new_status,
            metadata=new_metadata,
            references=new_references,
            history=new_history,
            tags=new_tags,
            notes=new_notes,
            is_favorite=new_is_favorite,
        )
        self._registry.register(record)
        return record

    @staticmethod
    def _build_event(event_type: VersionHistoryEventType, version_id: str, message: str) -> VersionHistory:
        checksum = CloudVersionManager._event_checksum(event_type, version_id, message)
        return VersionHistory(event_id=str(uuid.uuid4()), event_type=event_type, version_id=version_id, message=message, checksum=checksum)

    @staticmethod
    def _event_checksum(event_type: VersionHistoryEventType, version_id: str, message: str) -> str:
        payload = {"event_type": event_type.value, "version_id": version_id, "message": message}
        return compute_checksum(payload)

    @staticmethod
    def _record_checksum(
        subject_type: VersionSubjectType,
        subject_id: str,
        parent_version: str | None,
        version_number: int,
        snapshot_checksum: str,
        workspace_id: str | None,
        project_id: str | None,
        artifact_id: str | None,
        change_summary: str,
        author: str,
        status: VersionStatus,
        is_favorite: bool,
        tags: tuple[str, ...],
        notes: str,
        metadata: dict[str, Any],
        references: tuple[VersionReference, ...],
        history: tuple[VersionHistory, ...],
    ) -> str:
        payload = {
            "subject_type": subject_type.value,
            "subject_id": subject_id,
            "parent_version": parent_version,
            "version_number": version_number,
            "snapshot_checksum": snapshot_checksum,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "artifact_id": artifact_id,
            "change_summary": change_summary,
            "author": author,
            "status": status.value,
            "is_favorite": is_favorite,
            "tags": sorted(tags),
            "notes": notes,
            "metadata": metadata,
            "references": [reference.model_dump(mode="json") for reference in references],
            "history": [event.model_dump(mode="json", exclude={"event_id", "timestamp"}) for event in history],
        }
        return compute_checksum(payload)
