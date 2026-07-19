"""`app.cloud_platform.statistics`: per-workspace and registry-wide aggregation."""

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.statistics import aggregate_registry_statistics, compute_statistics


def test_compute_statistics_matches_reference_counts(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudCompiler().compile(cloud_platform_context)
    stats = compute_statistics(build.workspace)
    assert stats.project_count == 1
    assert stats.snapshot_count == 1
    assert stats.research_reference_count == 1
    assert stats.dataset_reference_count == 1
    assert stats.artifact_reference_count == 1
    assert stats.workspace_count == 1


def test_compute_statistics_is_deterministic(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudCompiler().compile(cloud_platform_context)
    stats1 = compute_statistics(build.workspace)
    stats2 = compute_statistics(build.workspace)
    assert stats1.checksum == stats2.checksum


def test_aggregate_registry_statistics_sums_across_builds(cloud_platform_context: CloudPlatformContext) -> None:
    compiler = CloudCompiler()
    build1 = compiler.compile(cloud_platform_context)
    other_context = CloudPlatformContext(workspace_id="workspace-2")
    build2 = compiler.compile(other_context)

    aggregate = aggregate_registry_statistics([build1, build2])
    assert aggregate["workspace_count"] == 2
    assert aggregate["project_count"] == 1
    assert aggregate["dataset_reference_count"] == 1


def test_aggregate_registry_statistics_empty() -> None:
    aggregate = aggregate_registry_statistics([])
    assert aggregate["workspace_count"] == 0
    assert aggregate["project_count"] == 0
