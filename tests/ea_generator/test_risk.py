"""Tests for app.ea_generator.risk."""

from app.ea_generator.models import EAGeneratorConfiguration
from app.ea_generator.risk import RiskCodeGenerator


def test_generates_risk_parameters_from_configuration() -> None:
    configuration = EAGeneratorConfiguration(magic_number=42, lot_size=0.5, stop_loss_points=30, take_profit_points=60, max_open_positions=2)
    risk = RiskCodeGenerator().generate(configuration)
    assert risk.magic_number == 42
    assert risk.lot_size == 0.5
    assert risk.stop_loss_points == 30
    assert risk.take_profit_points == 60
    assert risk.max_open_positions == 2


def test_default_configuration_produces_default_risk() -> None:
    risk = RiskCodeGenerator().generate(EAGeneratorConfiguration())
    assert risk.magic_number == 100000
    assert risk.lot_size == 0.1
    assert risk.max_open_positions == 1


def test_generation_is_deterministic() -> None:
    configuration = EAGeneratorConfiguration()
    generator = RiskCodeGenerator()
    assert generator.generate(configuration) == generator.generate(configuration)
