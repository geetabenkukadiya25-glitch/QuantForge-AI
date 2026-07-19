"""`app.cloud_platform.workspace_manager.WorkspaceValidator`: structural
checks over `CloudPlatformContext`s and compiled `WorkspaceRecord`s."""

import dataclasses

from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.workspace_manager import CloudWorkspaceManager, WorkspaceValidator


def test_validate_context_reuses_cloud_validator_for_invalid_workspace_id() -> None:
    result = WorkspaceValidator().validate_context(CloudPlatformContext(workspace_id=""))
    assert not result.is_valid


def test_validate_context_passes_for_a_valid_context(cloud_platform_context: CloudPlatformContext) -> None:
    result = WorkspaceValidator().validate_context(cloud_platform_context)
    assert result.is_valid


def test_validate_record_passes_for_a_freshly_created_workspace(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1")
    result = WorkspaceValidator().validate_record(record)
    assert result.is_valid
    assert result.errors == []


def test_validate_record_detects_checksum_mismatch(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1")
    tampered = record.model_copy(update={"checksum": "0" * 64})
    result = WorkspaceValidator().validate_record(tampered)
    assert not result.is_valid
    assert any("checksum" in issue.path for issue in result.errors)


def test_validate_record_detects_unsupported_schema_version(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1")
    tampered = record.model_copy(update={"schema_version": "99.0.0"})
    result = WorkspaceValidator().validate_record(tampered)
    assert not result.is_valid
    assert any("schema_version" in issue.path for issue in result.errors)


def test_validate_record_detects_duplicate_project_records(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1")
    record = workspace_manager.create_project("ws1", "p1", "Alpha")
    duplicated = record.model_copy(update={"project_records": record.project_records + record.project_records})
    result = WorkspaceValidator().validate_record(duplicated)
    assert not result.is_valid
    assert any("project_records" in issue.path for issue in result.errors)


def test_validate_record_full_lifecycle_stays_valid_after_many_operations(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    workspace_manager.create_workspace("ws1", label="Alpha")
    workspace_manager.create_project("ws1", "p1", "Project One", dataset_references=(dataset_reference,))
    workspace_manager.favorite_project("ws1", "p1", True)
    workspace_manager.set_project_tags("ws1", "p1", ("a", "b"))
    workspace_manager.rename_workspace("ws1", "Alpha Renamed")
    workspace_manager.snapshot_workspace("ws1", label="checkpoint")
    workspace_manager.archive_project("ws1", "p1")
    record = workspace_manager.favorite_workspace("ws1", True)

    result = WorkspaceValidator().validate_record(record)
    assert result.is_valid, result.errors
