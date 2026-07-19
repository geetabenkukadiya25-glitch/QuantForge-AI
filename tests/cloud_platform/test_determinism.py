"""Determinism: two `CloudPlatformEngine.execute()` calls over the same context
must produce the same checksum -- proving no random identity field leaked
into the checksummed payload (the recurring bug class caught in every
prior phase)."""

from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.engine import CloudPlatformEngine


def test_two_runs_of_the_same_context_produce_the_same_checksum(cloud_platform_context: CloudPlatformContext) -> None:
    engine = CloudPlatformEngine()
    build1 = engine.execute(cloud_platform_context)
    build2 = engine.execute(cloud_platform_context)
    assert build1.checksum == build2.checksum
    assert build1.result_id != build2.result_id


def test_workspace_and_project_checksums_are_identical_across_runs(cloud_platform_context: CloudPlatformContext) -> None:
    engine = CloudPlatformEngine()
    build1 = engine.execute(cloud_platform_context)
    build2 = engine.execute(cloud_platform_context)
    assert build1.workspace.checksum == build2.workspace.checksum
    assert build1.workspace.projects[0].checksum == build2.workspace.projects[0].checksum
    assert build1.workspace.snapshots[0].checksum == build2.workspace.snapshots[0].checksum


def test_statistics_checksum_is_identical_across_runs(cloud_platform_context: CloudPlatformContext) -> None:
    engine = CloudPlatformEngine()
    build1 = engine.execute(cloud_platform_context)
    build2 = engine.execute(cloud_platform_context)
    assert build1.statistics.checksum == build2.statistics.checksum


def test_checksum_changes_when_a_reference_is_added(cloud_platform_context: CloudPlatformContext) -> None:
    from app.cloud_platform.context import ProjectDraft

    engine = CloudPlatformEngine()
    base = engine.execute(cloud_platform_context)

    extra_context = CloudPlatformContext(
        workspace_id=cloud_platform_context.workspace_id,
        label=cloud_platform_context.label,
        projects=(ProjectDraft(project_id="project-2", name="Extra Project"),) + cloud_platform_context.projects,
        snapshots=cloud_platform_context.snapshots,
    )
    # snapshot in fixture references only project-1, so it stays valid.
    extended = engine.execute(extra_context)
    assert base.checksum != extended.checksum
