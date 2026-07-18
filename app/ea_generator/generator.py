"""Orchestrates one full EA generation: indicators, parameters, risk,
trade management, and final source assembly.

`EAGenerator` is a pure transform: given an `EAGeneratorContext` it
deterministically produces the generated MQL5 source text plus every
structured breakdown of it. It never trades, never connects to MT5 or
a broker, and never calls an external API -- an offline code generator
only.
"""

from dataclasses import dataclass

from app.ea_generator import templates
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.indicators import IndicatorCodeGenerator
from app.ea_generator.models import GeneratedIndicatorDeclaration, GeneratedInput, GeneratedRiskParameters, GeneratedTradeManagement
from app.ea_generator.parameters import ParameterCodeGenerator
from app.ea_generator.risk import RiskCodeGenerator
from app.ea_generator.statistics import EAGeneratorStatisticsEngine
from app.ea_generator.trade_management import TradeManagementCodeGenerator


@dataclass(frozen=True)
class GenerationArtifacts:
    """Every intermediate artifact produced by one `EAGenerator.generate()` call."""

    source_code: str
    inputs: tuple[GeneratedInput, ...]
    indicator_declarations: tuple[GeneratedIndicatorDeclaration, ...]
    risk_parameters: GeneratedRiskParameters
    trade_management: GeneratedTradeManagement


class EAGenerator:
    """Builds the complete generated MQL5 source and its structured breakdown."""

    def __init__(
        self,
        indicator_generator: IndicatorCodeGenerator | None = None,
        parameter_generator: ParameterCodeGenerator | None = None,
        risk_generator: RiskCodeGenerator | None = None,
        trade_management_generator: TradeManagementCodeGenerator | None = None,
        statistics_engine: EAGeneratorStatisticsEngine | None = None,
    ) -> None:
        self._indicator_generator = indicator_generator or IndicatorCodeGenerator()
        self._parameter_generator = parameter_generator or ParameterCodeGenerator()
        self._risk_generator = risk_generator or RiskCodeGenerator()
        self._trade_management_generator = trade_management_generator or TradeManagementCodeGenerator()
        self._statistics_engine = statistics_engine or EAGeneratorStatisticsEngine()

    def generate(self, context: EAGeneratorContext) -> GenerationArtifacts:
        strategy_model = context.strategy_model
        configuration = context.configuration

        inputs = self._parameter_generator.generate(context)
        indicator_declarations = self._indicator_generator.generate(strategy_model)
        risk_parameters = self._risk_generator.generate(configuration)
        trade_management = self._trade_management_generator.generate(strategy_model)

        source_code = templates.assemble(
            strategy_model=strategy_model,
            configuration=configuration,
            inputs=inputs,
            indicator_declarations=indicator_declarations,
            risk_parameters=risk_parameters,
            trade_management=trade_management,
        )

        return GenerationArtifacts(
            source_code=source_code,
            inputs=inputs,
            indicator_declarations=indicator_declarations,
            risk_parameters=risk_parameters,
            trade_management=trade_management,
        )
