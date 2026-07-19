"""Determinism: replaying the same sequence of version operations on two
independent `CloudVersionManager`s must produce identical checksums at
every level -- proving no random identity field (event_id, timestamps)
leaked into any checksummed payload."""

from app.cloud_platform.version_manager import CloudVersionManager
from app.cloud_platform.version_report import VersionReport
from app.cloud_platform.version_statistics import compute_version_registry_statistics
from app.cloud_platform.versioning import VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def _run_scenario(manager: CloudVersionManager):
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1), change_summary="init", author="system")
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1", change_summary="update")
    manager.favorite_version("v2", True)
    manager.set_version_tags("v2", ("gold", "trend"))
    manager.update_metadata("v2", {"k": "v"})
    manager.snapshot("v2", label="checkpoint")
    return manager.get_version("v2")


def test_two_independent_managers_produce_identical_final_checksum() -> None:
    record1 = _run_scenario(CloudVersionManager())
    record2 = _run_scenario(CloudVersionManager())
    assert record1.checksum == record2.checksum
    assert record1.version_number == record2.version_number


def test_history_event_checksums_are_identical_across_runs() -> None:
    record1 = _run_scenario(CloudVersionManager())
    record2 = _run_scenario(CloudVersionManager())
    assert [e.checksum for e in record1.history] == [e.checksum for e in record2.history]
    assert [e.event_id for e in record1.history] != [e.event_id for e in record2.history]


def test_statistics_checksum_is_identical_across_runs() -> None:
    manager1, manager2 = CloudVersionManager(), CloudVersionManager()
    _run_scenario(manager1)
    _run_scenario(manager2)
    stats1 = compute_version_registry_statistics(manager1.list_versions())
    stats2 = compute_version_registry_statistics(manager2.list_versions())
    assert stats1.checksum == stats2.checksum


def test_executive_report_summary_is_identical_across_runs() -> None:
    manager1, manager2 = CloudVersionManager(), CloudVersionManager()
    record1 = _run_scenario(manager1)
    record2 = _run_scenario(manager2)
    summary1 = VersionReport(record1, manager1.registry).executive_summary()
    summary2 = VersionReport(record2, manager2.registry).executive_summary()
    assert summary1["version"]["checksum"] == summary2["version"]["checksum"]
    assert summary1["statistics"]["checksum"] == summary2["statistics"]["checksum"]


def test_comparison_is_deterministic_across_runs() -> None:
    manager1, manager2 = CloudVersionManager(), CloudVersionManager()
    _run_scenario(manager1)
    _run_scenario(manager2)
    comparison1 = manager1.compare_versions("v1", "v2")
    comparison2 = manager2.compare_versions("v1", "v2")
    assert comparison1.differences == comparison2.differences
    assert comparison1.checksum_equal == comparison2.checksum_equal


def test_checksum_changes_when_snapshot_checksum_differs() -> None:
    def scenario(seed):
        manager = CloudVersionManager()
        return manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(seed))

    assert scenario("a").checksum != scenario("b").checksum
