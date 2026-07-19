"""Aggregate statistics over a compiled `CloudWorkspace`, and across a registry of many.

Pure computation over already-compiled models -- no filesystem access,
no networking, no business logic about what a "good" workspace looks
like. Reuses `app.core.checksums.compute_checksum`; hashing logic is
never duplicated here.
"""

from collections.abc import Iterable

from app.cloud_platform.models import CloudBuild, CloudStatistics, CloudWorkspace
from app.core.checksums import compute_checksum


def compute_statistics(workspace: CloudWorkspace) -> CloudStatistics:
    """Compute a deterministic `CloudStatistics` snapshot for one compiled workspace."""
    research_count = sum(len(p.research_references) for p in workspace.projects)
    dataset_count = sum(len(p.dataset_references) for p in workspace.projects)
    artifact_count = sum(len(p.artifact_references) for p in workspace.projects)
    payload = {
        "workspace_id": workspace.workspace_id,
        "project_count": len(workspace.projects),
        "snapshot_count": len(workspace.snapshots),
        "research_reference_count": research_count,
        "dataset_reference_count": dataset_count,
        "artifact_reference_count": artifact_count,
        "workspace_checksum": workspace.checksum,
    }
    checksum = compute_checksum(payload)
    return CloudStatistics(
        workspace_count=1,
        project_count=len(workspace.projects),
        snapshot_count=len(workspace.snapshots),
        research_reference_count=research_count,
        dataset_reference_count=dataset_count,
        artifact_reference_count=artifact_count,
        checksum=checksum,
    )


def aggregate_registry_statistics(builds: Iterable[CloudBuild]) -> dict:
    """Aggregate creation statistics across many registered `CloudBuild`s.

    Registry-wide view: total workspace count plus the sum of each
    workspace's own already-computed statistics. Never recomputes a
    workspace's own checksum or reference counts -- only sums them.
    """
    builds = list(builds)
    return {
        "workspace_count": len(builds),
        "project_count": sum(b.statistics.project_count for b in builds),
        "snapshot_count": sum(b.statistics.snapshot_count for b in builds),
        "research_reference_count": sum(b.statistics.research_reference_count for b in builds),
        "dataset_reference_count": sum(b.statistics.dataset_reference_count for b in builds),
        "artifact_reference_count": sum(b.statistics.artifact_reference_count for b in builds),
    }
