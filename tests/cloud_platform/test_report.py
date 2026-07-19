"""`app.cloud_platform.report`: executive report + read-only DataFrame views."""

import pandas as pd
import pytest

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.report import CloudPlatformReport, build_executive_report


@pytest.fixture
def build(cloud_platform_context: CloudPlatformContext):
    return CloudCompiler().compile(cloud_platform_context)


def test_build_executive_report_matches_statistics(build) -> None:
    report = build_executive_report(build)
    assert report.project_count == build.statistics.project_count
    assert report.checksum == build.checksum
    assert report.workspace_id == build.workspace.workspace_id


def test_executive_report_has_fresh_report_id_each_call(build) -> None:
    report1 = build_executive_report(build)
    report2 = build_executive_report(build)
    assert report1.report_id != report2.report_id
    assert report1.checksum == report2.checksum


def test_projects_report_is_a_dataframe(build) -> None:
    report = CloudPlatformReport(build)
    frame = report.projects_report()
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1
    assert frame.iloc[0]["project_id"] == "project-1"


def test_references_report_covers_all_reference_kinds(build) -> None:
    report = CloudPlatformReport(build)
    frame = report.references_report()
    assert set(frame["kind"]) == {"RESEARCH", "DATASET", "ARTIFACT"}


def test_summary_is_a_plain_dict(build) -> None:
    report = CloudPlatformReport(build)
    summary = report.summary()
    assert isinstance(summary, dict)
    assert summary["checksum"] == build.checksum
