"""Compiles a validated `CloudPlatformContext` into an immutable `CloudBuild`.

A pure transformation: given draft projects/snapshots/references, build
the final `CloudWorkspace` and its `CloudStatistics`, and their content
checksums -- the same discipline `ReplayCompiler`/`ValidationCompiler`
established. Every identity/timestamp field is excluded from a checksum
payload before hashing, so two compilations of the same context produce
the same checksums. Reuses `app.core.checksums.compute_checksum` --
hashing logic is never duplicated here.
"""

import uuid
from datetime import datetime, timezone

from app.cloud_platform.context import CloudPlatformContext, ProjectDraft
from app.cloud_platform.metadata import CLOUD_PLATFORM_RESULT_VERSION, WorkspaceMetadata
from app.cloud_platform.models import CloudBuild, CloudProject, CloudSnapshot, CloudWorkspace
from app.cloud_platform.statistics import compute_statistics
from app.core.checksums import compute_checksum
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CloudCompiler:
    """Builds a `CloudBuild` from one validated workspace context."""

    def compile(self, context: CloudPlatformContext) -> CloudBuild:
        projects = tuple(self._compile_project(draft) for draft in context.projects)
        project_checksum_by_id = {project.project_id: project.checksum for project in projects}
        snapshots = tuple(self._compile_snapshot(draft, context.workspace_id, project_checksum_by_id) for draft in context.snapshots)

        metadata = WorkspaceMetadata(workspace_id=context.workspace_id, label=context.label, result_version=CLOUD_PLATFORM_RESULT_VERSION)

        workspace_checksum = self._workspace_checksum(metadata, projects, context.project_references, snapshots)
        workspace = CloudWorkspace(
            workspace_id=context.workspace_id,
            metadata=metadata,
            projects=projects,
            project_references=context.project_references,
            snapshots=snapshots,
            checksum=workspace_checksum,
            created_at=datetime.now(timezone.utc),
        )

        statistics = compute_statistics(workspace)

        build_checksum = compute_checksum(
            {
                "metadata": metadata.model_dump(mode="json"),
                "workspace_checksum": workspace.checksum,
                "statistics_checksum": statistics.checksum,
            }
        )

        build = CloudBuild(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            workspace=workspace,
            statistics=statistics,
            checksum=build_checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled cloud build for workspace %s (checksum=%s)", context.workspace_id, build_checksum[:12])
        return build

    @staticmethod
    def _compile_project(draft: ProjectDraft) -> CloudProject:
        payload = {
            "project_id": draft.project_id,
            "name": draft.name,
            "research_references": [r.model_dump(mode="json") for r in draft.research_references],
            "dataset_references": [r.model_dump(mode="json") for r in draft.dataset_references],
            "artifact_references": [r.model_dump(mode="json") for r in draft.artifact_references],
        }
        checksum = compute_checksum(payload)
        return CloudProject(
            project_id=draft.project_id,
            name=draft.name,
            research_references=draft.research_references,
            dataset_references=draft.dataset_references,
            artifact_references=draft.artifact_references,
            checksum=checksum,
            created_at=draft.created_at or datetime.now(timezone.utc),
        )

    @staticmethod
    def _compile_snapshot(draft, workspace_id: str, project_checksum_by_id: dict[str, str]) -> CloudSnapshot:
        payload = {
            "snapshot_id": draft.snapshot_id,
            "workspace_id": workspace_id,
            "label": draft.label,
            "project_ids": list(draft.project_ids),
            "referenced_checksums": [project_checksum_by_id[pid] for pid in draft.project_ids],
        }
        checksum = compute_checksum(payload)
        return CloudSnapshot(
            snapshot_id=draft.snapshot_id,
            workspace_id=workspace_id,
            label=draft.label,
            project_ids=draft.project_ids,
            checksum=checksum,
            created_at=draft.created_at or datetime.now(timezone.utc),
        )

    @staticmethod
    def _workspace_checksum(metadata: WorkspaceMetadata, projects, project_references, snapshots) -> str:
        payload = {
            "metadata": metadata.model_dump(mode="json"),
            "project_checksums": [p.checksum for p in projects],
            "project_reference_checksums": sorted(r.checksum for r in project_references),
            "snapshot_checksums": [s.checksum for s in snapshots],
        }
        return compute_checksum(payload)
