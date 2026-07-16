"""Tests for ContextValidator."""

from app.context_engine.validator import ContextValidator


def test_valid_snapshot_passes(snapshot) -> None:
    result = ContextValidator().validate(snapshot)
    assert result.is_valid


def test_unsupported_version_reported(snapshot) -> None:
    stale = snapshot.model_copy(update={"context_version": "9.9.9"})
    result = ContextValidator().validate(stale)
    assert not result.is_valid
    assert any("context_version" in issue.path for issue in result.errors)


def test_holiday_unknown_produces_warning(snapshot) -> None:
    result = ContextValidator().validate(snapshot)
    assert any("is_holiday" in issue.path for issue in result.warnings)


def test_missing_higher_lower_timeframe_produces_warning(snapshot) -> None:
    result = ContextValidator().validate(snapshot)
    assert any(issue.path == "timeframe" for issue in result.warnings)


def test_report_is_human_readable(snapshot) -> None:
    stale = snapshot.model_copy(update={"context_version": "9.9.9"})
    report = ContextValidator().validate(stale).report()
    assert "FAILED" in report
    assert "context_version" in report


def test_session_datetime_outside_bounds_reported(snapshot) -> None:
    from datetime import timedelta

    shifted_market = snapshot.market.model_copy(
        update={"datetime_utc": snapshot.market.datetime_utc + timedelta(days=10)}
    )
    shifted = snapshot.model_copy(update={"market": shifted_market})
    result = ContextValidator().validate(shifted)
    assert not result.is_valid
    assert any("session" in issue.path for issue in result.errors)
