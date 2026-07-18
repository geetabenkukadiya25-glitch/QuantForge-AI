"""Tests for app.ea_generator.templates."""

from app.ea_generator import templates
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.indicators import IndicatorCodeGenerator
from app.ea_generator.models import EAGeneratorConfiguration
from app.ea_generator.parameters import ParameterCodeGenerator
from app.ea_generator.risk import RiskCodeGenerator
from app.ea_generator.trade_management import TradeManagementCodeGenerator


def test_render_header_includes_strategy_id_and_checksum(strategy_model_a) -> None:
    header = templates.render_header(strategy_model_a, EAGeneratorConfiguration())
    assert strategy_model_a.metadata.id in header
    assert strategy_model_a.checksum in header


def test_render_header_uses_ea_name_when_provided(strategy_model_a) -> None:
    configuration = EAGeneratorConfiguration(ea_name="My Custom EA")
    header = templates.render_header(strategy_model_a, configuration)
    assert "My Custom EA" in header


def test_render_header_falls_back_to_strategy_name(strategy_model_a) -> None:
    header = templates.render_header(strategy_model_a, EAGeneratorConfiguration())
    assert strategy_model_a.metadata.name in header


def test_render_inputs_lists_every_input() -> None:
    from app.ea_generator.models import GeneratedInput

    inputs = (GeneratedInput(name="InpLotSize", mql_type="double", default_value="0.1", comment="Lot size"),)
    rendered = templates.render_inputs(inputs, include_comments=True)
    assert "input double InpLotSize = 0.1;" in rendered
    assert "Lot size" in rendered


def test_render_inputs_omits_comments_when_disabled() -> None:
    from app.ea_generator.models import GeneratedInput

    inputs = (GeneratedInput(name="InpLotSize", mql_type="double", default_value="0.1", comment="Lot size"),)
    rendered = templates.render_inputs(inputs, include_comments=False)
    assert "Lot size" not in rendered


def test_render_indicator_declarations_handles_empty_tuple() -> None:
    rendered = templates.render_indicator_declarations((), include_comments=True)
    assert "none declared" in rendered


def test_render_indicator_declarations_lists_type(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    rendered = templates.render_indicator_declarations(declarations, include_comments=True)
    assert "SMA" in rendered


def test_render_risk_parameters_includes_magic_number() -> None:
    risk = RiskCodeGenerator().generate(EAGeneratorConfiguration(magic_number=777))
    rendered = templates.render_risk_parameters(risk, include_comments=True)
    assert "777" in rendered


def test_render_trade_management_lists_every_section(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    rendered = templates.render_trade_management(tm, include_comments=True)
    assert "Filters" in rendered
    assert "Entry Rules" in rendered
    assert "Exit Rules" in rendered


def test_render_trade_management_generates_stub_functions(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    rendered = templates.render_trade_management(tm, include_comments=True)
    assert "bool Check_entry_rules_buy_entry()" in rendered


def test_render_lifecycle_skeleton_has_oninit_ontick_ondeinit() -> None:
    rendered = templates.render_lifecycle_skeleton()
    assert "int OnInit()" in rendered
    assert "void OnTick()" in rendered
    assert "void OnDeinit(const int reason)" in rendered


def test_assemble_produces_nonempty_source(strategy_model_a) -> None:
    configuration = EAGeneratorConfiguration()
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=configuration)
    inputs = ParameterCodeGenerator().generate(context)
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    risk = RiskCodeGenerator().generate(configuration)
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    source = templates.assemble(strategy_model_a, configuration, inputs, declarations, risk, tm)
    assert source.strip() != ""
    assert source.endswith("\n")


def test_assemble_is_deterministic(strategy_model_a) -> None:
    configuration = EAGeneratorConfiguration()
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=configuration)
    inputs = ParameterCodeGenerator().generate(context)
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    risk = RiskCodeGenerator().generate(configuration)
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    first = templates.assemble(strategy_model_a, configuration, inputs, declarations, risk, tm)
    second = templates.assemble(strategy_model_a, configuration, inputs, declarations, risk, tm)
    assert first == second
