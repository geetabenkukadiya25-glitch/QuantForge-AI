"""Determinism: replaying the same sequence of artifact operations on two
independent `CloudArtifactManager`s must produce identical checksums at
every level -- proving no random identity field (event_id, timestamps)
leaked into any checksummed payload."""

from app.cloud_platform.artifact import ArtifactType
from app.cloud_platform.artifact_manager import CloudArtifactManager
from app.cloud_platform.artifact_report import ArtifactReport
from app.cloud_platform.artifact_statistics import compute_artifact_registry_statistics


def _run_scenario(manager: CloudArtifactManager):
    manager.create_artifact("a1", ArtifactType.DATASET, "Dataset A", source_module="data_engine", workspace_id="ws1")
    manager.create_artifact("a2", ArtifactType.STRATEGY, "Strategy B", dependencies=("a1",), workspace_id="ws1")
    manager.favorite_artifact("a2", True)
    manager.set_artifact_tags("a2", ("gold", "trend"))
    manager.rename_artifact("a2", "Strategy B Renamed")
    manager.update_metadata("a2", {"k": "v"})
    manager.snapshot_artifact("a2", label="checkpoint")
    return manager.get_artifact("a2")


def test_two_independent_managers_produce_identical_final_checksum() -> None:
    record1 = _run_scenario(CloudArtifactManager())
    record2 = _run_scenario(CloudArtifactManager())
    assert record1.checksum == record2.checksum
    assert record1.version == record2.version


def test_history_event_checksums_are_identical_across_runs() -> None:
    record1 = _run_scenario(CloudArtifactManager())
    record2 = _run_scenario(CloudArtifactManager())
    assert [e.checksum for e in record1.history] == [e.checksum for e in record2.history]
    assert [e.event_id for e in record1.history] != [e.event_id for e in record2.history]


def test_statistics_checksum_is_identical_across_runs() -> None:
    manager1, manager2 = CloudArtifactManager(), CloudArtifactManager()
    _run_scenario(manager1)
    _run_scenario(manager2)
    stats1 = compute_artifact_registry_statistics(manager1.list_artifacts())
    stats2 = compute_artifact_registry_statistics(manager2.list_artifacts())
    assert stats1.checksum == stats2.checksum


def test_executive_report_summary_is_identical_across_runs() -> None:
    manager1, manager2 = CloudArtifactManager(), CloudArtifactManager()
    record1 = _run_scenario(manager1)
    record2 = _run_scenario(manager2)
    summary1 = ArtifactReport(record1, manager1.registry).executive_summary()
    summary2 = ArtifactReport(record2, manager2.registry).executive_summary()
    assert summary1["artifact"]["checksum"] == summary2["artifact"]["checksum"]
    assert summary1["statistics"]["checksum"] == summary2["statistics"]["checksum"]


def test_checksum_changes_when_a_tag_differs() -> None:
    def scenario(tag: str):
        manager = CloudArtifactManager()
        manager.create_artifact("a1", ArtifactType.DATASET, "A")
        return manager.set_artifact_tags("a1", (tag,))

    assert scenario("a").checksum != scenario("b").checksum


def test_checksum_changes_when_dependencies_differ() -> None:
    def scenario(with_dependency: bool):
        manager = CloudArtifactManager()
        manager.create_artifact("a1", ArtifactType.DATASET, "A")
        dependencies = ("a1",) if with_dependency else ()
        return manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=dependencies)

    assert scenario(True).checksum != scenario(False).checksum
