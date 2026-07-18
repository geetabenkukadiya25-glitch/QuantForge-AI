"""`MissingInformationDetector`: the explicit "ask a human" list."""

from app.ai_extraction.missing_info import MissingInformationDetector


def test_symbol_is_always_flagged_missing() -> None:
    report = MissingInformationDetector().detect((), (), (), (), (), (), (), True, True)
    assert "symbol" in report.missing_items


def test_empty_extraction_flags_everything() -> None:
    report = MissingInformationDetector().detect((), (), (), (), (), (), (), False, False)
    assert set(report.missing_items) == {
        "strategy_name", "description", "entry_rules", "exit_rules", "indicators_or_detectors", "risk_management", "timeframes", "sessions", "symbol",
    }


def test_full_extraction_only_flags_symbol() -> None:
    from app.ai_extraction.models import IndicatorMention, RiskMention, RuleMention, SessionMention, TimeframeMention

    indicators = (IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=0.9),)
    entry_rules = (RuleMention(section="entry", raw_text="x", line_number=0, confidence=0.8),)
    exit_rules = (RuleMention(section="exit", raw_text="x", line_number=0, confidence=0.8),)
    risk = (RiskMention(category="stop_loss", raw_text="x", value=10.0, line_number=0, confidence=0.8),)
    sessions = (SessionMention(session_name="London", raw_text="x", line_number=0, confidence=0.9),)
    timeframes = (TimeframeMention(timeframe="H1", raw_text="x", line_number=0, confidence=0.9),)

    report = MissingInformationDetector().detect(indicators, (), entry_rules, exit_rules, risk, sessions, timeframes, True, True)
    assert report.missing_items == ("symbol",)


def test_warnings_have_matching_categories() -> None:
    report = MissingInformationDetector().detect((), (), (), (), (), (), (), False, False)
    warning_categories = {w.category for w in report.warnings}
    assert "entry_rules" in warning_categories
    assert "symbol" in warning_categories
