"""Small pure validation predicates (Phase 17.9) -- mirrors
`app.governance.governance_rules`'s shape. No I/O, no manager calls
beyond an optional caller-supplied registry lookup.
"""

from app.cloud_sync.artifact import Artifact
from app.cloud_sync.cloud_models import SyncOperation
from app.cloud_sync.provider_registry import ProviderRegistry
from app.cloud_sync.sync_policy import SyncPolicy
from app.cloud_sync.sync_policy import validate as _validate_policy


def validate_provider_id(provider_id: str | None, registry: ProviderRegistry) -> list[str]:
    if provider_id is None:
        return []
    if registry.get(provider_id) is None:
        return [f"Unknown provider id '{provider_id}'."]
    return []


def validate_operation(operation: SyncOperation) -> list[str]:
    issues = []
    if not operation.object_id.strip():
        issues.append("object_id must not be empty")
    if operation.retry_count < 0:
        issues.append("retry_count must be >= 0")
    return issues


def validate_artifact(artifact: Artifact) -> list[str]:
    issues = []
    if not artifact.object_id.strip():
        issues.append("object_id must not be empty")
    if not artifact.content_hash.strip():
        issues.append("content_hash must not be empty")
    if artifact.version < 1:
        issues.append("version must be >= 1")
    return issues


def validate_policy(policy: SyncPolicy) -> list[str]:
    return _validate_policy(policy)
