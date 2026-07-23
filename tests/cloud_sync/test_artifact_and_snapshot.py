"""`artifact.py`/`snapshot.py` -- hash reuse via `app.core.checksums.compute_checksum`."""

from app.core.checksums import compute_checksum
from app.cloud_sync.artifact import Artifact, ArtifactKind, ArtifactStatus, register_artifact
from app.cloud_sync.snapshot import Snapshot, SnapshotKind, create_snapshot


def test_register_artifact_hash_matches_shared_checksum_recipe() -> None:
    payload = {"id": "d-1", "name": "EURUSD"}
    artifact = register_artifact(ArtifactKind.DATASET, "d-1", payload)
    assert artifact.content_hash == compute_checksum(payload)
    assert artifact.status == ArtifactStatus.REGISTERED
    assert artifact.version == 1


def test_artifact_round_trip() -> None:
    artifact = register_artifact(ArtifactKind.STRATEGY, "s-1", {"a": 1}, owner="alice", tags=["fx"])
    restored = Artifact.from_dict(artifact.to_dict())
    assert restored.owner == "alice"
    assert restored.tags == ["fx"]
    assert restored.content_hash == artifact.content_hash


def test_create_snapshot_hash_is_order_independent() -> None:
    snap_a = create_snapshot(SnapshotKind.WORKSPACE, "A", ["ref2", "ref1"])
    snap_b = create_snapshot(SnapshotKind.WORKSPACE, "B", ["ref1", "ref2"])
    assert snap_a.content_hash == snap_b.content_hash  # sorted before hashing


def test_snapshot_round_trip() -> None:
    snapshot = create_snapshot(SnapshotKind.PROJECT, "Checkpoint", ["a", "b"], notes="pre-release")
    restored = Snapshot.from_dict(snapshot.to_dict())
    assert restored.object_refs == ["a", "b"]
    assert restored.notes == "pre-release"
