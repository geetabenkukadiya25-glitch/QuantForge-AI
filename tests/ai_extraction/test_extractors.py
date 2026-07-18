"""The 8 domain-specific extractors: pure, deterministic pattern matching
against real registered vocabularies (indicators, detectors, sessions,
timeframes) or regex/keyword heuristics (rules, risk, parameters)."""

from app.ai_extraction.extractors import (
    EntryRuleExtractor,
    ExitRuleExtractor,
    IndicatorExtractor,
    ParameterExtractor,
    RiskManagementExtractor,
    SessionExtractor,
    SmartMoneyExtractor,
    TimeframeExtractor,
)
from app.ai_extraction.parser import DocumentParser
from app.ai_extraction.sections import SectionDetector
from tests.ai_extraction.conftest import SAMPLE_MARKDOWN


def _pipeline(text: str = SAMPLE_MARKDOWN):
    parsed = DocumentParser().parse(text)
    sections = SectionDetector().detect(parsed)
    return parsed, sections


def test_indicator_extractor_matches_real_registered_names(indicator_registry) -> None:
    parsed, _ = _pipeline()
    mentions = IndicatorExtractor().extract(parsed.lines, indicator_registry, 200)
    types = {m.matched_type for m in mentions}
    assert types == {"SMA", "RSI"}


def test_indicator_extractor_does_not_false_positive_on_substrings(indicator_registry) -> None:
    parsed, _ = _pipeline()
    mentions = IndicatorExtractor().extract(parsed.lines, indicator_registry, 200)
    assert not any(m.matched_type == "WMA" for m in mentions)  # "slow_ma" must never match "WMA"


def test_indicator_extractor_falls_back_to_default_registry_when_none_given() -> None:
    parsed, _ = _pipeline()
    mentions = IndicatorExtractor().extract(parsed.lines, None, 200)
    assert any(m.matched_type == "SMA" for m in mentions)


def test_indicator_extractor_unknown_items_flags_unregistered_names(indicator_registry) -> None:
    text = "## Indicators\n- ZigZag Custom Oscillator\n"
    parsed, sections = _pipeline(text)
    unknown = IndicatorExtractor().unknown_items(sections, indicator_registry)
    assert any("ZigZag" in item for item in unknown)


def test_smart_money_extractor_matches_real_registered_names(smc_registry) -> None:
    text = "## Smart Money\n- Wait for an Order Block to form\n- Look for a Fair Value Gap\n"
    parsed, _ = _pipeline(text)
    mentions = SmartMoneyExtractor().extract(parsed.lines, smc_registry, 200)
    types = {m.matched_type for m in mentions}
    assert "Order Block" in types
    assert "Fair Value Gap" in types


def test_entry_rule_extractor_finds_bullets_in_entry_section() -> None:
    parsed, sections = _pipeline()
    mentions = EntryRuleExtractor().extract(parsed.lines, sections, 200)
    assert any("fast_ma crosses above slow_ma" in m.raw_text for m in mentions)
    assert all(m.section == "entry" for m in mentions)


def test_entry_rule_extractor_finds_keyword_mentions_outside_sections() -> None:
    parsed, sections = _pipeline("Some prose. Enter long when price breaks the high. More prose.")
    mentions = EntryRuleExtractor().extract(parsed.lines, sections, 200)
    assert any("enter long" in m.raw_text.lower() for m in mentions)
    assert all(m.confidence <= 0.5 for m in mentions)  # lower confidence outside a detected section


def test_exit_rule_extractor_finds_bullets_in_exit_section() -> None:
    parsed, sections = _pipeline()
    mentions = ExitRuleExtractor().extract(parsed.lines, sections, 200)
    assert any("fast_ma crosses below slow_ma" in m.raw_text for m in mentions)


def test_risk_management_extractor_finds_stop_loss_and_position_sizing() -> None:
    parsed, _ = _pipeline()
    mentions = RiskManagementExtractor().extract(parsed.lines, 200)
    categories = {m.category for m in mentions}
    assert "stop_loss" in categories
    assert "position_sizing" in categories
    stop_loss = next(m for m in mentions if m.category == "stop_loss")
    assert stop_loss.value == 20.0


def test_risk_management_extractor_no_match_produces_no_mentions() -> None:
    parsed, _ = _pipeline("Just some unrelated prose about markets.")
    mentions = RiskManagementExtractor().extract(parsed.lines, 200)
    assert mentions == ()


def test_session_extractor_matches_real_session_names() -> None:
    parsed, _ = _pipeline()
    mentions = SessionExtractor().extract(parsed.lines, 200)
    assert any(m.session_name == "London" for m in mentions)


def test_session_extractor_no_session_mentioned() -> None:
    parsed, _ = _pipeline("No trading window is mentioned here.")
    mentions = SessionExtractor().extract(parsed.lines, 200)
    assert mentions == ()


def test_timeframe_extractor_matches_real_timeframe_code() -> None:
    parsed, _ = _pipeline()
    mentions = TimeframeExtractor().extract(parsed.lines, 200)
    assert any(m.timeframe == "H1" for m in mentions)


def test_timeframe_extractor_matches_plain_english_alias() -> None:
    parsed, _ = _pipeline("Trade this strategy on the daily chart.")
    mentions = TimeframeExtractor().extract(parsed.lines, 200)
    assert any(m.timeframe == "D1" for m in mentions)


def test_parameter_extractor_associates_numbers_with_indicator_mentions(indicator_registry) -> None:
    parsed, _ = _pipeline()
    indicator_mentions = IndicatorExtractor().extract(parsed.lines, indicator_registry, 200)
    parameters = ParameterExtractor().extract(indicator_mentions, parsed.lines, 200)
    values = {(p.component_hint, p.value) for p in parameters}
    assert ("SMA", 20.0) in values
    assert ("SMA", 50.0) in values
    assert ("RSI", 14.0) in values
