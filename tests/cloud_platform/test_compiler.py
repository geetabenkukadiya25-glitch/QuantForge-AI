"""`app.cloud_platform.compiler`: deterministic `CloudBuild` construction."""

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft


def test_compile_produces_matching_project_and_snapshot_counts(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudCompiler().compile(cloud_platform_context)
    assert len(build.workspace.projects) == 1
    assert len(build.workspace.snapshots) == 1
    assert build.workspace.workspace_id == "workspace-1"


def test_compile_assigns_non_empty_checksums_at_every_level(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudCompiler().compile(cloud_platform_context)
    assert len(build.checksum) == 64
    assert len(build.workspace.checksum) == 64
    for project in build.workspace.projects:
        assert len(project.checksum) == 64
    for snapshot in build.workspace.snapshots:
        assert len(snapshot.checksum) == 64


def test_compile_preserves_supplied_reference_checksums(cloud_platform_context: CloudPlatformContext, dataset_reference) -> None:
    build = CloudCompiler().compile(cloud_platform_context)
    project = build.workspace.projects[0]
    assert project.dataset_references[0].checksum == dataset_reference.checksum


def test_project_checksum_changes_when_a_reference_changes(dataset_reference) -> None:
    draft_a = ProjectDraft(project_id="p1", name="A", dataset_references=(dataset_reference,))
    draft_b = ProjectDraft(project_id="p1", name="A", dataset_references=())
    build_a = CloudCompiler().compile(CloudPlatformContext(workspace_id="ws1", projects=(draft_a,)))
    build_b = CloudCompiler().compile(CloudPlatformContext(workspace_id="ws1", projects=(draft_b,)))
    assert build_a.workspace.projects[0].checksum != build_b.workspace.projects[0].checksum
    assert build_a.checksum != build_b.checksum


def test_snapshot_checksum_reflects_referenced_project_checksum(dataset_reference) -> None:
    draft = ProjectDraft(project_id="p1", name="A", dataset_references=(dataset_reference,))
    snapshot = SnapshotDraft(snapshot_id="s1", project_ids=("p1",))
    build = CloudCompiler().compile(CloudPlatformContext(workspace_id="ws1", projects=(draft,), snapshots=(snapshot,)))
    assert build.workspace.snapshots[0].workspace_id == "ws1"
    assert len(build.workspace.snapshots[0].checksum) == 64


def test_compile_generates_a_fresh_result_id_each_time(cloud_platform_context: CloudPlatformContext) -> None:
    compiler = CloudCompiler()
    build1 = compiler.compile(cloud_platform_context)
    build2 = compiler.compile(cloud_platform_context)
    assert build1.result_id != build2.result_id
