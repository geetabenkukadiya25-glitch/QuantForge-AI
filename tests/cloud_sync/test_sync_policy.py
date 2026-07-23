"""`sync_policy.py` -- defaults/validate, mirrors settings_center's section-module shape."""

from app.cloud_sync.sync_conflict import ConflictResolutionPolicy
from app.cloud_sync.sync_policy import SyncPolicy, defaults, validate


def test_defaults_are_manual_and_no_auto_retry() -> None:
    policy = defaults()
    assert policy.default_conflict_resolution == ConflictResolutionPolicy.MANUAL.value
    assert policy.auto_retry_enabled is False
    assert validate(policy) == []


def test_validate_rejects_unknown_resolution() -> None:
    policy = SyncPolicy(default_conflict_resolution="NOT_A_POLICY")
    issues = validate(policy)
    assert any("default_conflict_resolution" in issue for issue in issues)


def test_validate_rejects_negative_retry_count() -> None:
    policy = SyncPolicy(max_retry_count=-1)
    assert any("max_retry_count" in issue for issue in validate(policy))


def test_policy_round_trip() -> None:
    policy = SyncPolicy(default_conflict_resolution=ConflictResolutionPolicy.KEEP_LOCAL.value, per_kind_overrides={"DATASET": "KEEP_REMOTE"})
    restored = SyncPolicy.from_dict(policy.to_dict())
    assert restored.per_kind_overrides == {"DATASET": "KEEP_REMOTE"}
