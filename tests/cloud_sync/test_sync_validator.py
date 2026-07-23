"""`sync_validator.py` -- small pure predicates."""

from app.cloud_sync.artifact import Artifact, ArtifactKind
from app.cloud_sync.cloud_models import SyncKind, SyncOperation
from app.cloud_sync.provider_registry import DEFAULT_REGISTRY
from app.cloud_sync.sync_policy import SyncPolicy
from app.cloud_sync.sync_validator import validate_artifact, validate_operation, validate_policy, validate_provider_id


def test_validate_provider_id_none_is_valid() -> None:
    assert validate_provider_id(None, DEFAULT_REGISTRY) == []


def test_validate_provider_id_known() -> None:
    assert validate_provider_id("github", DEFAULT_REGISTRY) == []


def test_validate_provider_id_unknown() -> None:
    issues = validate_provider_id("nonexistent", DEFAULT_REGISTRY)
    assert len(issues) == 1


def test_validate_operation_empty_object_id() -> None:
    op = SyncOperation(kind=SyncKind.DATASET, object_id="")
    assert any("object_id" in issue for issue in validate_operation(op))


def test_validate_artifact_missing_hash() -> None:
    artifact = Artifact(kind=ArtifactKind.DATASET, object_id="d-1", content_hash="")
    assert any("content_hash" in issue for issue in validate_artifact(artifact))


def test_validate_policy_delegates_to_sync_policy_module() -> None:
    policy = SyncPolicy(max_retry_count=-5)
    assert any("max_retry_count" in issue for issue in validate_policy(policy))
