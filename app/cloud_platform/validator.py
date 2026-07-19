"""Pre-compile validation for a `CloudPlatformContext`.

Structural checks only -- duplicate ids, invalid references, checksum
*format* integrity (a well-formed SHA-256 hex digest; the Cloud Platform
never recomputes another engine's checksum, only stores what it was
given), metadata completeness, schema version, duplicate project names,
invalid timestamps, and invalid workspace structure. No business logic:
this validator has no opinion on what a "good" strategy, dataset, or
research result looks like -- only on whether the reference metadata
describing one is internally consistent.
"""

import re
from dataclasses import dataclass

from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.metadata import CLOUD_SCHEMA_VERSION

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class CloudIssue:
    """One validation failure: where it occurred and why."""

    path: str
    message: str


@dataclass(frozen=True)
class CloudCheckResult:
    """The outcome of validating one `CloudPlatformContext`."""

    issues: tuple[CloudIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    @property
    def errors(self) -> list[CloudIssue]:
        return list(self.issues)


class CloudValidator:
    """Validates a `CloudPlatformContext` before it is compiled into a `CloudBuild`."""

    def validate(self, context: CloudPlatformContext) -> CloudCheckResult:
        issues: list[CloudIssue] = []
        issues.extend(self._check_workspace_structure(context))
        issues.extend(self._check_schema_version())
        issues.extend(self._check_duplicate_project_ids(context))
        issues.extend(self._check_duplicate_project_names(context))
        issues.extend(self._check_reference_integrity(context))
        issues.extend(self._check_snapshots(context))
        issues.extend(self._check_timestamps(context))
        return CloudCheckResult(issues=tuple(issues))

    @staticmethod
    def _check_workspace_structure(context: CloudPlatformContext) -> list[CloudIssue]:
        issues: list[CloudIssue] = []
        if not context.workspace_id or context.workspace_id != context.workspace_id.strip():
            issues.append(CloudIssue("workspace_id", "workspace_id must be non-empty and free of leading/trailing whitespace."))
        for draft in context.projects:
            if not draft.project_id or not draft.project_id.strip():
                issues.append(CloudIssue("projects[].project_id", "project_id must be non-empty."))
            if not draft.name or not draft.name.strip():
                issues.append(CloudIssue(f"projects[{draft.project_id}].name", "Project name must be non-empty."))
        return issues

    @staticmethod
    def _check_schema_version() -> list[CloudIssue]:
        if not _SCHEMA_VERSION_RE.match(CLOUD_SCHEMA_VERSION):
            return [CloudIssue("schema_version", f"Malformed schema version: {CLOUD_SCHEMA_VERSION!r}.")]
        return []

    @staticmethod
    def _check_duplicate_project_ids(context: CloudPlatformContext) -> list[CloudIssue]:
        seen: set[str] = set()
        issues: list[CloudIssue] = []
        for draft in context.projects:
            if draft.project_id in seen:
                issues.append(CloudIssue("projects[].project_id", f"Duplicate project_id: {draft.project_id!r}."))
            seen.add(draft.project_id)
        return issues

    @staticmethod
    def _check_duplicate_project_names(context: CloudPlatformContext) -> list[CloudIssue]:
        seen: set[str] = set()
        issues: list[CloudIssue] = []
        for draft in context.projects:
            if draft.name in seen:
                issues.append(CloudIssue("projects[].name", f"Duplicate project name: {draft.name!r}."))
            seen.add(draft.name)
        return issues

    def _check_reference_integrity(self, context: CloudPlatformContext) -> list[CloudIssue]:
        issues: list[CloudIssue] = []
        seen_reference_ids: set[str] = set()

        def check_reference(ref, path: str) -> None:
            if ref.reference_id in seen_reference_ids:
                issues.append(CloudIssue(path, f"Duplicate reference_id: {ref.reference_id!r}."))
            seen_reference_ids.add(ref.reference_id)
            if not _SHA256_HEX_RE.match(ref.checksum):
                issues.append(CloudIssue(path, f"Malformed checksum for reference {ref.reference_id!r}: expected a 64-character SHA-256 hex digest."))
            if not ref.name or not ref.name.strip():
                issues.append(CloudIssue(path, f"Reference {ref.reference_id!r} has an empty name."))

        for pref in context.project_references:
            check_reference(pref, "project_references[]")
        for draft in context.projects:
            for ref in draft.research_references:
                check_reference(ref, f"projects[{draft.project_id}].research_references[]")
            for ref in draft.dataset_references:
                check_reference(ref, f"projects[{draft.project_id}].dataset_references[]")
            for ref in draft.artifact_references:
                check_reference(ref, f"projects[{draft.project_id}].artifact_references[]")
        return issues

    @staticmethod
    def _check_snapshots(context: CloudPlatformContext) -> list[CloudIssue]:
        issues: list[CloudIssue] = []
        known_project_ids = {draft.project_id for draft in context.projects}
        seen_snapshot_ids: set[str] = set()
        for snapshot in context.snapshots:
            if not snapshot.snapshot_id or not snapshot.snapshot_id.strip():
                issues.append(CloudIssue("snapshots[].snapshot_id", "snapshot_id must be non-empty."))
            if snapshot.snapshot_id in seen_snapshot_ids:
                issues.append(CloudIssue("snapshots[].snapshot_id", f"Duplicate snapshot_id: {snapshot.snapshot_id!r}."))
            seen_snapshot_ids.add(snapshot.snapshot_id)
            for project_id in snapshot.project_ids:
                if project_id not in known_project_ids:
                    issues.append(CloudIssue(f"snapshots[{snapshot.snapshot_id}].project_ids", f"Snapshot references unknown project_id: {project_id!r}."))
        return issues

    @staticmethod
    def _check_timestamps(context: CloudPlatformContext) -> list[CloudIssue]:
        issues: list[CloudIssue] = []

        def check_timestamp(created_at, path: str) -> None:
            if created_at is None:
                return
            if created_at.tzinfo is None:
                issues.append(CloudIssue(path, "created_at must be timezone-aware."))

        for draft in context.projects:
            check_timestamp(draft.created_at, f"projects[{draft.project_id}].created_at")
        for snapshot in context.snapshots:
            check_timestamp(snapshot.created_at, f"snapshots[{snapshot.snapshot_id}].created_at")
        return issues
