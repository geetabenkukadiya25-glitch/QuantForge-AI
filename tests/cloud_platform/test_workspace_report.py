"""`app.cloud_platform.workspace_report`: executive/workspace/project/history/
statistics/validation summaries. No charts."""

import pandas as pd

from app.cloud_platform.workspace_manager import CloudWorkspaceManager
from app.cloud_platform.workspace_report import WorkspaceReport


def _built_record(workspace_manager: CloudWorkspaceManager, dataset_reference):
    workspace_manager.create_workspace("ws1", label="Alpha")
    workspace_manager.create_project("ws1", "p1", "Project One", dataset_references=(dataset_reference,))
    return workspace_manager.favorite_project("ws1", "p1", True)


def test_workspace_summary_matches_record(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    report = WorkspaceReport(record)
    summary = report.workspace_summary()
    assert summary["workspace_id"] == "ws1"
    assert summary["label"] == "Alpha"
    assert summary["checksum"] == record.checksum


def test_project_summary_is_a_dataframe_with_lifecycle_state(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    frame = WorkspaceReport(record).project_summary()
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1
    assert frame.iloc[0]["project_id"] == "p1"
    assert bool(frame.iloc[0]["is_favorite"]) is True


def test_history_summary_covers_every_event(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    frame = WorkspaceReport(record).history_summary()
    assert len(frame) == len(record.history)
    assert list(frame["event_type"]) == [event.event_type.value for event in record.history]


def test_statistics_summary_is_a_plain_dict(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    summary = WorkspaceReport(record).statistics_summary()
    assert isinstance(summary, dict)
    assert summary["project_count"] == 1


def test_validation_summary_reports_valid(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    summary = WorkspaceReport(record).validation_summary()
    assert summary["is_valid"] is True
    assert summary["issues"] == []


def test_executive_summary_combines_every_section(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    record = _built_record(workspace_manager, dataset_reference)
    summary = WorkspaceReport(record).executive_summary()
    assert set(summary.keys()) == {"workspace", "statistics", "validation", "cloud_build"}
    assert summary["cloud_build"]["checksum"] == record.build.checksum
