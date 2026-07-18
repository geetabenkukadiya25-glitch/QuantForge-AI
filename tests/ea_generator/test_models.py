"""Tests for app.ea_generator.models."""

import pytest
from pydantic import ValidationError

from app.ea_generator.metadata import EA_RESULT_VERSION, EAGeneratorMetadata
from app.ea_generator.models import (
    EAGeneratorConfiguration,
    EAGeneratorResult,
    EAGeneratorStatistics,
    GeneratedIndicatorDeclaration,
    GeneratedInput,
    GeneratedRiskParameters,
    GeneratedRuleBlock,
    GeneratedTradeManagement,
)


def _metadata(**overrides) -> EAGeneratorMetadata:
    defaults = dict(ea_id="ea-1", strategy_id="strategy-1", strategy_checksum="abc123", output_filename="EA.mq5")
    defaults.update(overrides)
    return EAGeneratorMetadata(**defaults)


def _risk() -> GeneratedRiskParameters:
    return GeneratedRiskParameters(magic_number=1, lot_size=0.1, stop_loss_points=10, take_profit_points=20, max_open_positions=1)


def test_configuration_defaults() -> None:
    cfg = EAGeneratorConfiguration()
    assert cfg.output_filename == "GeneratedEA.mq5"
    assert cfg.magic_number == 100000
    assert cfg.lot_size == 0.1
    assert cfg.max_open_positions == 1
    assert cfg.include_comments is True


def test_configuration_is_frozen() -> None:
    cfg = EAGeneratorConfiguration()
    with pytest.raises(ValidationError):
        cfg.magic_number = 5  # type: ignore[misc]


def test_configuration_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorConfiguration(unexpected_field=1)  # type: ignore[call-arg]


def test_configuration_rejects_non_positive_lot_size() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorConfiguration(lot_size=0)


def test_configuration_rejects_negative_stop_loss() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorConfiguration(stop_loss_points=-1)


def test_configuration_rejects_zero_max_open_positions() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorConfiguration(max_open_positions=0)


def test_metadata_default_result_version() -> None:
    metadata = _metadata()
    assert metadata.result_version == EA_RESULT_VERSION


def test_metadata_is_frozen() -> None:
    metadata = _metadata()
    with pytest.raises(ValidationError):
        metadata.strategy_id = "other"  # type: ignore[misc]


def test_metadata_requires_nonempty_ea_id() -> None:
    with pytest.raises(ValidationError):
        _metadata(ea_id="")


def test_generated_input_holds_fields() -> None:
    item = GeneratedInput(name="InpLotSize", mql_type="double", default_value="0.1", comment="Lot size")
    assert item.name == "InpLotSize"
    assert item.mql_type == "double"


def test_generated_indicator_declaration_default_parameters_empty() -> None:
    decl = GeneratedIndicatorDeclaration(local_name="fast_sma", component_kind="indicator", type="SMA")
    assert decl.parameters == ()
    assert decl.timeframe is None


def test_generated_risk_parameters_validates_positive_lot_size() -> None:
    with pytest.raises(ValidationError):
        GeneratedRiskParameters(magic_number=1, lot_size=0, stop_loss_points=0, take_profit_points=0, max_open_positions=1)


def test_generated_rule_block_requires_condition() -> None:
    with pytest.raises(ValidationError):
        GeneratedRuleBlock(section="entry_rules", local_name="rule1", condition="")


def test_generated_trade_management_defaults_empty() -> None:
    tm = GeneratedTradeManagement()
    assert tm.filters == ()
    assert tm.entry_rules == ()
    assert tm.exit_rules == ()


def test_statistics_requires_nonnegative_counts() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorStatistics(total_indicators=-1, total_detectors=0, total_rules=0, total_inputs=0, source_line_count=0, source_character_count=0)


def test_result_requires_nonempty_source_code() -> None:
    with pytest.raises(ValidationError):
        EAGeneratorResult(
            result_id="r1",
            metadata=_metadata(),
            configuration=EAGeneratorConfiguration(),
            source_code="",
            risk_parameters=_risk(),
            trade_management=GeneratedTradeManagement(),
            statistics=EAGeneratorStatistics(total_indicators=0, total_detectors=0, total_rules=0, total_inputs=0, source_line_count=0, source_character_count=0),
            checksum="deadbeef",
        )


def test_result_builds_with_minimal_fields() -> None:
    result = EAGeneratorResult(
        result_id="r1",
        metadata=_metadata(),
        configuration=EAGeneratorConfiguration(),
        source_code="// generated",
        risk_parameters=_risk(),
        trade_management=GeneratedTradeManagement(),
        statistics=EAGeneratorStatistics(total_indicators=0, total_detectors=0, total_rules=0, total_inputs=0, source_line_count=1, source_character_count=12),
        checksum="deadbeef",
    )
    assert result.source_code == "// generated"
    assert result.inputs == ()
    assert result.built_at is not None


def test_result_is_frozen() -> None:
    result = EAGeneratorResult(
        result_id="r1",
        metadata=_metadata(),
        configuration=EAGeneratorConfiguration(),
        source_code="// generated",
        risk_parameters=_risk(),
        trade_management=GeneratedTradeManagement(),
        statistics=EAGeneratorStatistics(total_indicators=0, total_detectors=0, total_rules=0, total_inputs=0, source_line_count=1, source_character_count=12),
        checksum="deadbeef",
    )
    with pytest.raises(ValidationError):
        result.checksum = "other"  # type: ignore[misc]
