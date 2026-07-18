"""Translates a `StrategyModel`'s indicators/detectors into declaration blocks.

Reuses `app.strategy_builder`'s already-resolved `IndicatorReference`/
`DetectorReference` list directly -- never re-resolves the Indicator
Engine or Smart Money Engine registries, never recomputes anything.
Deterministic: iterates `StrategyModel.indicators`/`.detectors` in their
already-fixed tuple order, and sorts each component's parameter keys.
"""

import json

from app.ea_generator.models import GeneratedIndicatorDeclaration
from app.strategy_builder.models import StrategyModel


class IndicatorCodeGenerator:
    """Builds `GeneratedIndicatorDeclaration`s from a `StrategyModel`."""

    def generate(self, strategy_model: StrategyModel) -> tuple[GeneratedIndicatorDeclaration, ...]:
        declarations: list[GeneratedIndicatorDeclaration] = []

        for indicator in strategy_model.indicators:
            params = json.loads(indicator.parameters_json)
            declarations.append(
                GeneratedIndicatorDeclaration(
                    local_name=indicator.local_name,
                    component_kind="indicator",
                    type=indicator.type,
                    parameters=tuple(f"{key}={params[key]}" for key in sorted(params)),
                    timeframe=indicator.timeframe,
                )
            )

        for detector in strategy_model.detectors:
            params = json.loads(detector.parameters_json)
            declarations.append(
                GeneratedIndicatorDeclaration(
                    local_name=detector.local_name,
                    component_kind="detector",
                    type=detector.type,
                    parameters=tuple(f"{key}={params[key]}" for key in sorted(params)),
                    timeframe=detector.timeframe,
                )
            )

        return tuple(declarations)
