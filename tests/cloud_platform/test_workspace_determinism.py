"""Determinism: replaying the same sequence of workspace operations on two
independent `CloudWorkspaceManager`s must produce identical checksums at
every level -- proving no random identity field (event_id, record_id
timestamps) leaked into any checksummed payload."""

from app.cloud_platform.models import DatasetReference
from app.cloud_platform.workspace_manager import CloudWorkspaceManager
from app.cloud_platform.workspace_report import WorkspaceReport
from app.cloud_platform.workspace_statistics import compute_workspace_statistics
from app.core.checksums import compute_checksum


def _run_scenario(manager: CloudWorkspaceManager):
    ds = DatasetReference(reference_id="d1", name="XAUUSD_M5", symbol="XAUUSD", timeframe="M5", checksum=compute_checksum({"seed": "ds"}))
    manager.create_workspace("ws1", label="Alpha")
    manager.create_project("ws1", "p1", "Project One", dataset_references=(ds,))
    manager.favorite_project("ws1", "p1", True)
    manager.set_project_tags("ws1", "p1", ("gold", "trend"))
    manager.rename_workspace("ws1", "Alpha Renamed")
    manager.snapshot_workspace("ws1", label="checkpoint")
    manager.favorite_workspace("ws1", True)
    return manager.get_workspace("ws1")


def test_two_independent_managers_produce_identical_final_checksum() -> None:
    record1 = _run_scenario(CloudWorkspaceManager())
    record2 = _run_scenario(CloudWorkspaceManager())
    assert record1.checksum == record2.checksum
    assert record1.version == record2.version


def test_history_event_checksums_are_identical_across_runs() -> None:
    record1 = _run_scenario(CloudWorkspaceManager())
    record2 = _run_scenario(CloudWorkspaceManager())
    assert [e.checksum for e in record1.history] == [e.checksum for e in record2.history]
    # event_id is random -- must differ
    assert [e.event_id for e in record1.history] != [e.event_id for e in record2.history]


def test_underlying_build_checksum_is_identical_across_runs() -> None:
    record1 = _run_scenario(CloudWorkspaceManager())
    record2 = _run_scenario(CloudWorkspaceManager())
    assert record1.build.checksum == record2.build.checksum
    assert record1.build.result_id != record2.build.result_id


def test_statistics_checksum_is_identical_across_runs() -> None:
    record1 = _run_scenario(CloudWorkspaceManager())
    record2 = _run_scenario(CloudWorkspaceManager())
    assert compute_workspace_statistics(record1).checksum == compute_workspace_statistics(record2).checksum


def test_executive_report_summary_is_identical_across_runs() -> None:
    record1 = _run_scenario(CloudWorkspaceManager())
    record2 = _run_scenario(CloudWorkspaceManager())
    summary1 = WorkspaceReport(record1).executive_summary()
    summary2 = WorkspaceReport(record2).executive_summary()
    assert summary1["workspace"]["checksum"] == summary2["workspace"]["checksum"]
    assert summary1["statistics"]["checksum"] == summary2["statistics"]["checksum"]
    assert summary1["cloud_build"]["checksum"] == summary2["cloud_build"]["checksum"]


def test_checksum_changes_when_a_tag_differs() -> None:
    def scenario(tag: str):
        manager = CloudWorkspaceManager()
        manager.create_workspace("ws1")
        return manager.set_workspace_tags("ws1", (tag,))

    assert scenario("a").checksum != scenario("b").checksum
