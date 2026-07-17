"""`ValidationReport`."""

from app.validation_engine.report import ValidationReport
from app.validation_engine.runner import ValidationRunner


def test_walk_forward_report_has_one_row_per_window(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    df = ValidationReport(result).walk_forward_report()
    assert len(df) == result.walk_forward_result.total_windows
    assert "status" in df.columns


def test_monte_carlo_report_has_one_row_per_iteration(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    df = ValidationReport(result).monte_carlo_report()
    assert len(df) == result.monte_carlo_result.iterations_run


def test_robustness_confidence_stability_reports_are_dicts(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    report = ValidationReport(result)
    assert isinstance(report.robustness_report(), dict)
    assert isinstance(report.confidence_report(), dict)
    assert isinstance(report.stability_report(), dict)
    assert report.robustness_report()["robustness_score"] == result.robustness_score.robustness_score


def test_validation_summary_contains_top_level_scores(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    summary = ValidationReport(result).validation_summary()
    assert summary["checksum"] == result.checksum
    assert summary["candidate_id"] == result.metadata.candidate_id
