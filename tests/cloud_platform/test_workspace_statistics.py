"""`app.cloud_platform.workspace_statistics`: per-workspace and registry-wide aggregation."""

from app.cloud_platform.workspace_manager import CloudWorkspaceManager
from app.cloud_platform.workspace_statistics import aggregate_workspace_statistics, compute_workspace_statistics


def test_compute_workspace_statistics_matches_lifecycle_state(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    workspace_manager.create_workspace("ws1", label="Alpha")
    workspace_manager.create_project("ws1", "p1", "Project One", dataset_references=(dataset_reference,))
    workspace_manager.favorite_project("ws1", "p1", True)
    workspace_manager.set_project_tags("ws1", "p1", ("a", "b"))
    workspace_manager.set_workspace_tags("ws1", ("c",))
    record = workspace_manager.favorite_workspace("ws1", True)

    stats = compute_workspace_statistics(record)
    assert stats.workspace_count == 1
    assert stats.active_workspaces == 1
    assert stats.archived_workspaces == 0
    assert stats.deleted_workspaces == 0
    assert stats.project_count == 1
    assert stats.favorite_count == 2  # workspace + project
    assert stats.tag_count == 3  # "a", "b", "c"
    assert stats.history_count == len(record.history)


def test_compute_workspace_statistics_is_deterministic(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1")
    stats1 = compute_workspace_statistics(record)
    stats2 = compute_workspace_statistics(record)
    assert stats1.checksum == stats2.checksum


def test_metadata_completeness_reflects_filled_fields(workspace_manager: CloudWorkspaceManager) -> None:
    empty_record = workspace_manager.create_workspace("ws-empty")
    empty_stats = compute_workspace_statistics(empty_record)
    assert empty_stats.metadata_completeness == 0.0

    workspace_manager.create_workspace("ws-full", label="Alpha")
    workspace_manager.set_workspace_notes("ws-full", "Some notes")
    full_record = workspace_manager.set_workspace_tags("ws-full", ("x",))
    full_stats = compute_workspace_statistics(full_record)
    assert full_stats.metadata_completeness == 1.0


def test_aggregate_workspace_statistics_sums_across_records(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_workspace("ws2")
    workspace_manager.archive_workspace("ws2")

    aggregate = aggregate_workspace_statistics(workspace_manager.list_workspaces())
    assert aggregate["workspace_count"] == 2
    assert aggregate["active_workspaces"] == 1
    assert aggregate["archived_workspaces"] == 1


def test_aggregate_workspace_statistics_empty() -> None:
    aggregate = aggregate_workspace_statistics([])
    assert aggregate["workspace_count"] == 0
