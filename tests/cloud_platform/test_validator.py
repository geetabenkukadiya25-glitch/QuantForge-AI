"""`app.cloud_platform.validator`: structural pre-compile checks.

No business logic is exercised here -- only ids, names, checksum
*format*, timestamps, and workspace/snapshot structure.
"""

from datetime import datetime, timezone

from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft
from app.cloud_platform.models import DatasetReference
from app.cloud_platform.validator import CloudValidator


def test_valid_context_passes(cloud_platform_context: CloudPlatformContext) -> None:
    result = CloudValidator().validate(cloud_platform_context)
    assert result.is_valid
    assert result.errors == []


def test_empty_workspace_id_is_invalid() -> None:
    result = CloudValidator().validate(CloudPlatformContext(workspace_id=""))
    assert not result.is_valid


def test_whitespace_padded_workspace_id_is_invalid() -> None:
    result = CloudValidator().validate(CloudPlatformContext(workspace_id=" ws1 "))
    assert not result.is_valid


def test_duplicate_project_ids_are_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="A"), ProjectDraft(project_id="p1", name="B")),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate project_id" in issue.message for issue in result.errors)


def test_duplicate_project_names_are_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="Same"), ProjectDraft(project_id="p2", name="Same")),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate project name" in issue.message for issue in result.errors)


def test_malformed_checksum_is_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="A", dataset_references=(DatasetReference(reference_id="d1", name="D1", checksum="not-a-sha256"),)),),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("Malformed checksum" in issue.message for issue in result.errors)


def test_duplicate_reference_ids_across_projects_are_invalid() -> None:
    ref_kwargs = {"reference_id": "same-id", "name": "D", "checksum": "a" * 64}
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(
            ProjectDraft(project_id="p1", name="A", dataset_references=(DatasetReference(**ref_kwargs),)),
            ProjectDraft(project_id="p2", name="B", dataset_references=(DatasetReference(**ref_kwargs),)),
        ),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate reference_id" in issue.message for issue in result.errors)


def test_snapshot_referencing_unknown_project_is_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="A"),),
        snapshots=(SnapshotDraft(snapshot_id="s1", project_ids=("does-not-exist",)),),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("unknown project_id" in issue.message for issue in result.errors)


def test_duplicate_snapshot_ids_are_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        snapshots=(SnapshotDraft(snapshot_id="s1"), SnapshotDraft(snapshot_id="s1")),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate snapshot_id" in issue.message for issue in result.errors)


def test_naive_timestamp_on_project_draft_is_invalid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="A", created_at=datetime(2024, 1, 1)),),
    )
    result = CloudValidator().validate(context)
    assert not result.is_valid
    assert any("timezone-aware" in issue.message for issue in result.errors)


def test_timezone_aware_timestamp_on_project_draft_is_valid() -> None:
    context = CloudPlatformContext(
        workspace_id="ws1",
        projects=(ProjectDraft(project_id="p1", name="A", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),),
    )
    result = CloudValidator().validate(context)
    assert result.is_valid


def test_empty_project_name_is_invalid() -> None:
    context = CloudPlatformContext(workspace_id="ws1", projects=(ProjectDraft(project_id="p1", name=""),))
    result = CloudValidator().validate(context)
    assert not result.is_valid
