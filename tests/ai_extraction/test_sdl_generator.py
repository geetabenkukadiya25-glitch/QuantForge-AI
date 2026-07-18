"""`SDLGenerator`: assembles extracted mentions into a draft `StrategyDefinition`."""

from app.ai_extraction.analyzer import StrategyOverview
from app.ai_extraction.models import DetectorMention, IndicatorMention, RiskMention, RuleMention, SessionMention, TimeframeMention
from app.ai_extraction.sdl_generator import SDLGenerator
from app.sdl.validator import StrategyValidator


def _overview(name: str = "Golden Cross Strategy") -> StrategyOverview:
    return StrategyOverview(name=name, description="A test strategy.", name_detected=True, description_detected=True)


def test_generated_definition_passes_sdl_schema_validation() -> None:
    overview = _overview()
    indicators = (IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=0.9),)
    entry_rules = (RuleMention(section="entry", raw_text="Buy when fast_ma > slow_ma", line_number=0, confidence=0.8),)
    exit_rules = (RuleMention(section="exit", raw_text="Exit when fast_ma < slow_ma", line_number=0, confidence=0.8),)
    timeframes = (TimeframeMention(timeframe="H1", raw_text="x", line_number=0, confidence=0.9),)
    sessions = (SessionMention(session_name="London", raw_text="x", line_number=0, confidence=0.9),)

    definition = SDLGenerator().generate(overview, indicators, (), entry_rules, exit_rules, (), sessions, timeframes)
    result = StrategyValidator().validate(definition)
    assert result.is_valid, result.report()


def test_symbol_defaults_to_unknown_placeholder() -> None:
    definition = SDLGenerator().generate(_overview(), (), (), (), (), (), (), ())
    assert definition.symbols == ["UNKNOWN"]


def test_timeframe_defaults_to_unknown_placeholder_when_none_detected() -> None:
    definition = SDLGenerator().generate(_overview(), (), (), (), (), (), (), ())
    assert definition.timeframes == ["UNKNOWN"]


def test_detected_timeframes_are_used_and_sorted() -> None:
    timeframes = (TimeframeMention(timeframe="H4", raw_text="x", line_number=0, confidence=0.9), TimeframeMention(timeframe="H1", raw_text="x", line_number=1, confidence=0.9))
    definition = SDLGenerator().generate(_overview(), (), (), (), (), (), (), timeframes)
    assert definition.timeframes == ["H1", "H4"]


def test_indicators_and_detectors_both_land_in_the_single_indicators_field() -> None:
    """SDL's `indicators:` list holds both indicator AND detector
    references generically -- Strategy Builder resolves each by
    checking both registries (see app.strategy_builder.resolution)."""
    indicators = (IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=0.9),)
    detectors = (DetectorMention(matched_type="Order Block", raw_text="x", line_number=0, confidence=0.9),)
    definition = SDLGenerator().generate(_overview(), indicators, detectors, (), (), (), (), ())
    types = {spec.type for spec in definition.indicators}
    assert types == {"SMA", "Order Block"}


def test_duplicate_matched_types_are_deduplicated() -> None:
    indicators = (
        IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=0.9),
        IndicatorMention(matched_type="SMA", raw_text="y", line_number=1, confidence=0.9),
    )
    definition = SDLGenerator().generate(_overview(), indicators, (), (), (), (), (), ())
    assert len(definition.indicators) == 1


def test_rule_conditions_are_carried_through_verbatim_as_descriptive_text() -> None:
    entry_rules = (RuleMention(section="entry", raw_text="price closes above resistance", line_number=0, confidence=0.5),)
    definition = SDLGenerator().generate(_overview(), (), (), entry_rules, (), (), (), ())
    assert definition.entry_rules[0].condition == "price closes above resistance"


def test_risk_management_uses_position_sizing_mention() -> None:
    risk = (RiskMention(category="position_sizing", raw_text="Risk 1% per trade", value=1.0, line_number=0, confidence=0.8),)
    definition = SDLGenerator().generate(_overview(), (), (), (), (), risk, (), ())
    assert definition.risk_management is not None
    assert definition.risk_management.max_risk_per_trade_pct == 1.0


def test_trade_management_uses_stop_loss_and_take_profit_mentions() -> None:
    risk = (
        RiskMention(category="stop_loss", raw_text="Stop loss 20 pips", value=20.0, line_number=0, confidence=0.8),
        RiskMention(category="take_profit", raw_text="Take profit 40 pips", value=40.0, line_number=1, confidence=0.8),
    )
    definition = SDLGenerator().generate(_overview(), (), (), (), (), risk, (), ())
    assert definition.trade_management is not None
    assert definition.trade_management.stop_loss.value == 20.0
    assert definition.trade_management.take_profit.value == 40.0


def test_notes_flag_this_as_a_draft_requiring_review() -> None:
    definition = SDLGenerator().generate(_overview(), (), (), (), (), (), (), ())
    assert "human review" in definition.notes.lower()
    assert "draft" in definition.tags
