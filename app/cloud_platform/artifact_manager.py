"""Offline Local Artifact Registry orchestration (Phase 17.2).

`CloudArtifactManager` is the single entrypoint for every artifact
lifecycle operation (create, rename, archive, restore, soft-delete,
favorite, tags, notes, version increment, snapshot, reference update,
metadata update, dependency tracking). It manages ONLY metadata and
references about research artifacts already produced elsewhere in
QuantForge AI -- it is NOT cloud storage, NOT a filesystem indexer, and
it never inspects an artifact's actual content. Every mutation produces
a brand-new immutable `ArtifactRecord` with an incremented version and
an appended, checksummed history event; nothing is ever mutated in
place. Reuses -- never duplicates -- `app.core.checksums.compute_checksum`
and the same lifecycle-record discipline
`app.cloud_platform.workspace_manager.CloudWorkspaceManager` established.
100% offline: no authentication, no users, no networking, no database,
no broker/MetaTrader/execution-engine code of any kind.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.cloud_platform.artifact import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactHistoryEvent,
    ArtifactHistoryEventType,
    ArtifactRecord,
    ArtifactStatus,
    ArtifactType,
)
from app.cloud_platform.artifact_registry import CloudArtifactRegistry, find_dependency_cycle
from app.cloud_platform.exceptions import CloudPlatformError
from app.cloud_platform.models import ArtifactReference
from app.core.checksums import compute_checksum
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactAlreadyExistsError(CloudPlatformError):
    """Raised when creating an artifact id that's already registered."""


class InvalidArtifactStateError(CloudPlatformError):
    """Raised for an operation that is not valid given an artifact's current status."""


class DependencyNotFoundError(CloudPlatformError):
    """Raised when a declared dependency id isn't a registered artifact."""


class DependencyCycleError(CloudPlatformError):
    """Raised when adding a dependency would create a dependency cycle."""


class ArtifactValidationError(CloudPlatformError):
    """Raised when an artifact mutation would fail structural validation.

    Carries the full list of `ArtifactIssue`s for a complete report.
    """

    def __init__(self, issues: list["ArtifactIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Artifact mutation failed validation: {summary}")


@dataclass(frozen=True)
class ArtifactIssue:
    """One validation failure: where it occurred and why."""

    path: str
    message: str


@dataclass(frozen=True)
class ArtifactCheckResult:
    """The outcome of validating a new artifact, a compiled `ArtifactRecord`, or a registry."""

    issues: tuple[ArtifactIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def errors(self) -> list[ArtifactIssue]:
        return list(self.issues)


class ArtifactValidator:
    """Validates artifact creation, compiled `ArtifactRecord`s, and registries.

    Structural checks only: duplicate ids, duplicate checksums, invalid
    references, broken dependency chains, invalid versions, checksum
    mismatch, history mismatch, and metadata errors. No business logic
    about what a "good" dataset/strategy/report looks like.
    """

    def validate_new(
        self,
        artifact_id: str,
        name: str,
        dependencies: tuple[str, ...],
        references: tuple[ArtifactReference, ...],
        registry: CloudArtifactRegistry,
    ) -> ArtifactCheckResult:
        issues: list[ArtifactIssue] = []
        if not artifact_id or not artifact_id.strip():
            issues.append(ArtifactIssue("artifact_id", "artifact_id must be non-empty."))
        elif registry.is_registered(artifact_id):
            issues.append(ArtifactIssue("artifact_id", f"Duplicate artifact_id: {artifact_id!r}."))
        if not name or not name.strip():
            issues.append(ArtifactIssue("name", "Artifact name must be non-empty."))
        issues.extend(self._check_references(references))
        issues.extend(self._check_dependencies_exist(dependencies, registry))
        return ArtifactCheckResult(issues=tuple(issues))

    def validate_record(self, record: ArtifactRecord, registry: CloudArtifactRegistry | None = None) -> ArtifactCheckResult:
        issues: list[ArtifactIssue] = []
        issues.extend(self._check_checksum_integrity(record))
        issues.extend(self._check_history_consistency(record))
        issues.extend(self._check_version(record))
        issues.extend(self._check_metadata(record))
        issues.extend(self._check_references(record.references))
        if registry is not None:
            issues.extend(self._check_dependencies_exist(record.dependencies, registry))
            issues.extend(self._check_dependency_cycle(registry))
        return ArtifactCheckResult(issues=tuple(issues))

    def validate_registry(self, records: list[ArtifactRecord]) -> ArtifactCheckResult:
        """Registry-wide checks that need the full record set: duplicate checksums
        shared by two currently non-deleted artifacts."""
        issues: list[ArtifactIssue] = []
        seen: dict[str, str] = {}
        for record in records:
            if record.status == ArtifactStatus.DELETED:
                continue
            if record.checksum in seen:
                issues.append(ArtifactIssue("checksum", f"Duplicate checksum shared by {seen[record.checksum]!r} and {record.artifact_id!r}."))
            else:
                seen[record.checksum] = record.artifact_id
        return ArtifactCheckResult(issues=tuple(issues))

    @staticmethod
    def _check_references(references: tuple[ArtifactReference, ...]) -> list[ArtifactIssue]:
        issues: list[ArtifactIssue] = []
        for reference in references:
            if not _SHA256_HEX_RE.match(reference.checksum):
                issues.append(ArtifactIssue("references", f"Malformed checksum for reference {reference.reference_id!r}: expected a 64-character SHA-256 hex digest."))
        return issues

    @staticmethod
    def _check_dependencies_exist(dependencies: tuple[str, ...], registry: CloudArtifactRegistry) -> list[ArtifactIssue]:
        issues: list[ArtifactIssue] = []
        for dependency_id in dependencies:
            if not registry.is_registered(dependency_id):
                issues.append(ArtifactIssue("dependencies", f"Broken dependency chain: unknown artifact_id {dependency_id!r}."))
        return issues

    @staticmethod
    def _check_dependency_cycle(registry: CloudArtifactRegistry) -> list[ArtifactIssue]:
        cycle = find_dependency_cycle(registry.dependency_graph())
        if cycle is not None:
            return [ArtifactIssue("dependencies", f"Dependency cycle detected: {' -> '.join(cycle)}.")]
        return []

    @staticmethod
    def _check_checksum_integrity(record: ArtifactRecord) -> list[ArtifactIssue]:
        recomputed = CloudArtifactManager._record_checksum(
            record.artifact_type,
            record.name,
            record.description,
            record.workspace_id,
            record.project_id,
            record.source_module,
            record.status,
            record.is_favorite,
            record.tags,
            record.notes,
            record.dependencies,
            record.references,
            record.metadata,
            record.history,
        )
        if recomputed != record.checksum:
            return [ArtifactIssue("checksum", "Stored checksum does not match a recomputation of the record's own content.")]
        return []

    @staticmethod
    def _check_history_consistency(record: ArtifactRecord) -> list[ArtifactIssue]:
        issues: list[ArtifactIssue] = []
        versions = [event.version for event in record.history]
        if versions != sorted(versions):
            issues.append(ArtifactIssue("history", "History event versions are not monotonically non-decreasing."))
        if versions and versions[-1] > record.version:
            issues.append(ArtifactIssue("history", f"Latest history event version ({versions[-1]}) exceeds the record's own version ({record.version})."))
        seen_event_ids: set[str] = set()
        for event in record.history:
            if event.event_id in seen_event_ids:
                issues.append(ArtifactIssue("history", f"Duplicate event_id: {event.event_id!r}."))
            seen_event_ids.add(event.event_id)
        return issues

    @staticmethod
    def _check_version(record: ArtifactRecord) -> list[ArtifactIssue]:
        issues: list[ArtifactIssue] = []
        if record.version < 1:
            issues.append(ArtifactIssue("version", "version must be >= 1."))
        if record.schema_version != ARTIFACT_SCHEMA_VERSION:
            issues.append(ArtifactIssue("schema_version", f"Unsupported artifact schema version: {record.schema_version!r}."))
        return issues

    @staticmethod
    def _check_metadata(record: ArtifactRecord) -> list[ArtifactIssue]:
        issues: list[ArtifactIssue] = []
        for key in record.metadata:
            if not isinstance(key, str) or not key:
                issues.append(ArtifactIssue("metadata", f"Metadata keys must be non-empty strings, got {key!r}."))
        return issues


class CloudArtifactManager:
    """Creates and mutates local, offline research artifact records."""

    def __init__(self, registry: CloudArtifactRegistry | None = None, validator: ArtifactValidator | None = None) -> None:
        self._registry = registry or CloudArtifactRegistry()
        self._validator = validator or ArtifactValidator()

    @property
    def registry(self) -> CloudArtifactRegistry:
        return self._registry

    # -- Create -------------------------------------------------------------

    def create_artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        description: str = "",
        workspace_id: str | None = None,
        project_id: str | None = None,
        source_module: str = "",
        dependencies: tuple[str, ...] = (),
        references: tuple[ArtifactReference, ...] = (),
        tags: tuple[str, ...] = (),
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        metadata = dict(metadata or {})
        dependencies = tuple(dependencies)
        references = tuple(references)
        tags = tuple(tags)

        check = self._validator.validate_new(artifact_id, name, dependencies, references, self._registry)
        if not check.is_valid:
            raise ArtifactValidationError([ArtifactIssue(issue.path, issue.message) for issue in check.errors])

        event = self._build_event(ArtifactHistoryEventType.CREATED, artifact_id, version=1, message=name)
        checksum = self._record_checksum(
            artifact_type, name, description, workspace_id, project_id, source_module,
            ArtifactStatus.ACTIVE, False, tags, notes, dependencies, references, metadata, (event,),
        )
        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            description=description,
            workspace_id=workspace_id,
            project_id=project_id,
            source_module=source_module,
            version=1,
            checksum=checksum,
            status=ArtifactStatus.ACTIVE,
            tags=tags,
            notes=notes,
            dependencies=dependencies,
            references=references,
            metadata=metadata,
            is_favorite=False,
            history=(event,),
        )
        self._registry.register(record)
        logger.info("Created artifact %s (%s).", artifact_id, artifact_type.value)
        return record

    # -- Lifecycle ------------------------------------------------------------

    def rename_artifact(self, artifact_id: str, new_name: str) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        self._guard_not_deleted(current, "rename")
        if not new_name or not new_name.strip():
            raise ArtifactValidationError([ArtifactIssue("name", "Artifact name must be non-empty.")])
        return self._apply(artifact_id, ArtifactHistoryEventType.RENAMED, message=new_name, name=new_name)

    def archive_artifact(self, artifact_id: str) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        if current.status != ArtifactStatus.ACTIVE:
            raise InvalidArtifactStateError(f"Only an ACTIVE artifact can be archived (artifact {artifact_id!r} is {current.status.value}).")
        return self._apply(artifact_id, ArtifactHistoryEventType.ARCHIVED, status=ArtifactStatus.ARCHIVED)

    def restore_artifact(self, artifact_id: str) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        if current.status == ArtifactStatus.ACTIVE:
            raise InvalidArtifactStateError(f"Artifact {artifact_id!r} is already ACTIVE.")
        return self._apply(artifact_id, ArtifactHistoryEventType.RESTORED, status=ArtifactStatus.ACTIVE)

    def delete_artifact(self, artifact_id: str) -> ArtifactRecord:
        """Soft delete only -- the record and its full history are never physically removed."""
        current = self._registry.load(artifact_id)
        if current.status == ArtifactStatus.DELETED:
            raise InvalidArtifactStateError(f"Artifact {artifact_id!r} is already deleted.")
        return self._apply(artifact_id, ArtifactHistoryEventType.DELETED, status=ArtifactStatus.DELETED)

    def favorite_artifact(self, artifact_id: str, favorite: bool = True) -> ArtifactRecord:
        self._registry.load(artifact_id)
        return self._apply(artifact_id, ArtifactHistoryEventType.FAVORITE_CHANGED, is_favorite=favorite, message=str(favorite))

    def set_artifact_tags(self, artifact_id: str, tags: tuple[str, ...]) -> ArtifactRecord:
        self._registry.load(artifact_id)
        return self._apply(artifact_id, ArtifactHistoryEventType.TAG_CHANGED, tags=tuple(tags))

    def set_artifact_notes(self, artifact_id: str, notes: str) -> ArtifactRecord:
        self._registry.load(artifact_id)
        return self._apply(artifact_id, ArtifactHistoryEventType.NOTES_UPDATED, notes=notes)

    def increment_version(self, artifact_id: str, message: str = "") -> ArtifactRecord:
        """Explicitly marks a new version of this artifact's underlying content
        (e.g. a dataset was re-generated, a report was re-run). This registry
        never inspects the artifact's actual content -- pair this with
        `update_references`/`update_metadata` if the new content's own
        checksum needs to be recorded."""
        self._registry.load(artifact_id)
        return self._apply(artifact_id, ArtifactHistoryEventType.VERSION_INCREMENTED, message=message)

    def snapshot_artifact(self, artifact_id: str, label: str = "") -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        self._guard_not_deleted(current, "snapshot")
        return self._apply(artifact_id, ArtifactHistoryEventType.SNAPSHOT_TAKEN, message=label)

    def update_references(self, artifact_id: str, references: tuple[ArtifactReference, ...]) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        self._guard_not_deleted(current, "update references on")
        references = tuple(references)
        issues = self._validator._check_references(references)
        if issues:
            raise ArtifactValidationError(issues)
        return self._apply(artifact_id, ArtifactHistoryEventType.REFERENCE_UPDATED, references=references)

    def update_metadata(self, artifact_id: str, metadata: dict[str, Any]) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        self._guard_not_deleted(current, "update metadata on")
        return self._apply(artifact_id, ArtifactHistoryEventType.METADATA_UPDATED, metadata=dict(metadata))

    def add_dependency(self, artifact_id: str, dependency_artifact_id: str) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        self._guard_not_deleted(current, "add a dependency to")
        if dependency_artifact_id == artifact_id:
            raise DependencyCycleError(f"Artifact {artifact_id!r} cannot depend on itself.")
        if not self._registry.is_registered(dependency_artifact_id):
            raise DependencyNotFoundError(f"Unknown dependency artifact_id: {dependency_artifact_id!r}.")

        if dependency_artifact_id in current.dependencies:
            new_dependencies = current.dependencies
        else:
            new_dependencies = current.dependencies + (dependency_artifact_id,)
            graph = self._registry.dependency_graph()
            graph[artifact_id] = new_dependencies
            cycle = find_dependency_cycle(graph)
            if cycle is not None:
                raise DependencyCycleError(f"Adding dependency {dependency_artifact_id!r} to {artifact_id!r} would create a cycle: {' -> '.join(cycle)}.")

        return self._apply(artifact_id, ArtifactHistoryEventType.DEPENDENCY_ADDED, message=dependency_artifact_id, dependencies=new_dependencies)

    # -- Read access -------------------------------------------------------

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        return self._registry.load(artifact_id)

    def list_artifacts(self, include_disabled: bool = True) -> list[ArtifactRecord]:
        return self._registry.list(include_disabled=include_disabled)

    def version_history(self, artifact_id: str) -> list[ArtifactRecord]:
        return self._registry.version_history(artifact_id)

    # -- Internal helpers ----------------------------------------------------

    @staticmethod
    def _guard_not_deleted(record: ArtifactRecord, action: str) -> None:
        if record.status == ArtifactStatus.DELETED:
            raise InvalidArtifactStateError(f"Cannot {action} a deleted artifact {record.artifact_id!r}.")

    def _apply(
        self,
        artifact_id: str,
        event_type: ArtifactHistoryEventType,
        *,
        message: str = "",
        name: str | None = None,
        status: ArtifactStatus | None = None,
        is_favorite: bool | None = None,
        tags: tuple[str, ...] | None = None,
        notes: str | None = None,
        dependencies: tuple[str, ...] | None = None,
        references: tuple[ArtifactReference, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        current = self._registry.load(artifact_id)
        new_name = name if name is not None else current.name
        new_status = status if status is not None else current.status
        new_is_favorite = is_favorite if is_favorite is not None else current.is_favorite
        new_tags = tags if tags is not None else current.tags
        new_notes = notes if notes is not None else current.notes
        new_dependencies = dependencies if dependencies is not None else current.dependencies
        new_references = references if references is not None else current.references
        new_metadata = metadata if metadata is not None else current.metadata
        new_version = current.version + 1

        event = self._build_event(event_type, artifact_id, version=new_version, message=message)
        new_history = current.history + (event,)

        checksum = self._record_checksum(
            current.artifact_type, new_name, current.description, current.workspace_id, current.project_id, current.source_module,
            new_status, new_is_favorite, new_tags, new_notes, new_dependencies, new_references, new_metadata, new_history,
        )

        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=current.artifact_type,
            name=new_name,
            description=current.description,
            workspace_id=current.workspace_id,
            project_id=current.project_id,
            source_module=current.source_module,
            version=new_version,
            checksum=checksum,
            creation_time=current.creation_time,
            modified_time=datetime.now(timezone.utc),
            status=new_status,
            tags=new_tags,
            notes=new_notes,
            dependencies=new_dependencies,
            references=new_references,
            metadata=new_metadata,
            is_favorite=new_is_favorite,
            history=new_history,
        )
        self._registry.register(record)
        return record

    @staticmethod
    def _build_event(event_type: ArtifactHistoryEventType, artifact_id: str, version: int, message: str) -> ArtifactHistoryEvent:
        checksum = CloudArtifactManager._event_checksum(event_type, artifact_id, version, message)
        return ArtifactHistoryEvent(event_id=str(uuid.uuid4()), event_type=event_type, artifact_id=artifact_id, version=version, message=message, checksum=checksum)

    @staticmethod
    def _event_checksum(event_type: ArtifactHistoryEventType, artifact_id: str, version: int, message: str) -> str:
        payload = {"event_type": event_type.value, "artifact_id": artifact_id, "version": version, "message": message}
        return compute_checksum(payload)

    @staticmethod
    def _record_checksum(
        artifact_type: ArtifactType,
        name: str,
        description: str,
        workspace_id: str | None,
        project_id: str | None,
        source_module: str,
        status: ArtifactStatus,
        is_favorite: bool,
        tags: tuple[str, ...],
        notes: str,
        dependencies: tuple[str, ...],
        references: tuple[ArtifactReference, ...],
        metadata: dict[str, Any],
        history: tuple[ArtifactHistoryEvent, ...],
    ) -> str:
        payload = {
            "artifact_type": artifact_type.value,
            "name": name,
            "description": description,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "source_module": source_module,
            "status": status.value,
            "is_favorite": is_favorite,
            "tags": sorted(tags),
            "notes": notes,
            "dependencies": sorted(dependencies),
            "references": [reference.model_dump(mode="json") for reference in references],
            "metadata": metadata,
            "history": [event.model_dump(mode="json", exclude={"event_id", "timestamp"}) for event in history],
        }
        return compute_checksum(payload)
