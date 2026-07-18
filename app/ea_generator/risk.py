"""Resolves the generated EA's risk-management parameters.

A pure, deterministic mapping from `EAGeneratorConfiguration` onto
`GeneratedRiskParameters` -- no live account, broker, or MT5 state is
ever read; every value comes from the caller-supplied configuration.
"""

from app.ea_generator.models import EAGeneratorConfiguration, GeneratedRiskParameters


class RiskCodeGenerator:
    """Builds the `GeneratedRiskParameters` block for one EA generation."""

    def generate(self, configuration: EAGeneratorConfiguration) -> GeneratedRiskParameters:
        return GeneratedRiskParameters(
            magic_number=configuration.magic_number,
            lot_size=configuration.lot_size,
            stop_loss_points=configuration.stop_loss_points,
            take_profit_points=configuration.take_profit_points,
            max_open_positions=configuration.max_open_positions,
        )
