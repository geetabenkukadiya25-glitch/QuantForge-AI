"""`sync_conflict.py` -- classification is pure/caller-supplied, and
resolution is never automatic."""

from datetime import datetime, timedelta

from app.cloud_sync.sync_conflict import ConflictKind, ConflictResolutionPolicy, SyncConflict, classify_conflict, resolve_conflict


def test_no_conflict_when_hashes_match() -> None:
    assert classify_conflict("abc", "abc", None, None) is None


def test_no_conflict_when_hash_missing() -> None:
    assert classify_conflict(None, "abc", None, None) is None
    assert classify_conflict("abc", None, None, None) is None


def test_hash_mismatch_without_timestamps() -> None:
    assert classify_conflict("abc", "def", None, None) == ConflictKind.HASH_MISMATCH


def test_remote_newer() -> None:
    now = datetime.now()
    assert classify_conflict("abc", "def", now, now + timedelta(minutes=5)) == ConflictKind.REMOTE_NEWER


def test_local_newer() -> None:
    now = datetime.now()
    assert classify_conflict("abc", "def", now + timedelta(minutes=5), now) == ConflictKind.LOCAL_NEWER


def test_resolve_conflict_is_explicit_and_never_automatic() -> None:
    conflict = SyncConflict(operation_id="op-1", artifact_id="art-1", kind=ConflictKind.HASH_MISMATCH)
    assert conflict.resolution is None
    resolved = resolve_conflict(conflict, ConflictResolutionPolicy.KEEP_LOCAL, notes="chose local")
    assert resolved.resolution == ConflictResolutionPolicy.KEEP_LOCAL
    assert resolved.resolved_at is not None
    assert resolved.notes == "chose local"


def test_conflict_round_trip() -> None:
    conflict = SyncConflict(operation_id="op-1", artifact_id="art-1", kind=ConflictKind.RENAME_CONFLICT, local_hash="a", remote_hash="b")
    restored = SyncConflict.from_dict(conflict.to_dict())
    assert restored.kind == ConflictKind.RENAME_CONFLICT
    assert restored.local_hash == "a"
