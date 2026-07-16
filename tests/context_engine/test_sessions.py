"""Tests for app.context_engine.sessions."""

from datetime import datetime, timezone

from app.context_engine.sessions import get_active_session, is_market_open, is_weekend, to_utc


def test_get_active_session_tokyo() -> None:
    moment = datetime(2024, 1, 3, 7, 0, tzinfo=timezone.utc)
    info = get_active_session(moment)
    assert info.name == "Tokyo"
    assert 0 <= info.progress_pct <= 100
    assert info.session_open < moment < info.session_close


def test_get_active_session_sydney_wraps_midnight() -> None:
    late = datetime(2024, 1, 3, 23, 0, tzinfo=timezone.utc)
    early = datetime(2024, 1, 4, 2, 0, tzinfo=timezone.utc)
    assert get_active_session(late).name == "Sydney"
    assert get_active_session(early).name == "Sydney"


def test_get_active_session_progress_increases_over_time() -> None:
    # 10:00 and 14:00 are both within London-only hours (Tokyo ends at 09:00),
    # so both timestamps resolve to the same session and are comparable.
    start = datetime(2024, 1, 3, 10, 0, tzinfo=timezone.utc)
    later = datetime(2024, 1, 3, 14, 0, tzinfo=timezone.utc)
    start_info = get_active_session(start)
    later_info = get_active_session(later)
    assert start_info.name == later_info.name == "London"
    assert later_info.progress_pct > start_info.progress_pct


def test_is_weekend_saturday() -> None:
    assert is_weekend(datetime(2024, 1, 6, 12, 0, tzinfo=timezone.utc)) is True


def test_is_weekend_sunday_before_reopen() -> None:
    assert is_weekend(datetime(2024, 1, 7, 10, 0, tzinfo=timezone.utc)) is True


def test_is_weekend_sunday_after_reopen() -> None:
    assert is_weekend(datetime(2024, 1, 7, 22, 0, tzinfo=timezone.utc)) is False


def test_is_weekend_friday_after_close() -> None:
    assert is_weekend(datetime(2024, 1, 5, 22, 0, tzinfo=timezone.utc)) is True


def test_is_weekend_weekday() -> None:
    assert is_weekend(datetime(2024, 1, 3, 12, 0, tzinfo=timezone.utc)) is False


def test_is_market_open_matches_inverse_of_weekend() -> None:
    moment = datetime(2024, 1, 3, 12, 0, tzinfo=timezone.utc)
    assert is_market_open(moment) == (not is_weekend(moment))


def test_to_utc_naive_assumed_utc() -> None:
    naive = datetime(2024, 1, 3, 12, 0)
    converted = to_utc(naive)
    assert converted.tzinfo == timezone.utc
    assert converted.hour == 12


def test_to_utc_aware_converted() -> None:
    from datetime import timedelta

    tz = timezone(timedelta(hours=5))
    aware = datetime(2024, 1, 3, 12, 0, tzinfo=tz)
    converted = to_utc(aware)
    assert converted.tzinfo == timezone.utc
    assert converted.hour == 7
