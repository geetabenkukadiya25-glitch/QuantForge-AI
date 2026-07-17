"""Resolves an SDL document's named components against the indicator/detector registries.

A pure function: given a `StrategyContext`, classify every SDL
`IndicatorSpec` as a resolved indicator (its `type` is registered in
`IndicatorRegistry`), a resolved detector (its `type` is registered in
`SMCRegistry`), missing (registered in neither), or ambiguous
(registered in both) -- then collect every filter/entry/exit rule as a
`RuleReference`. `StrategyValidator` and `StrategyCompiler` both consume
this same result, so the classification logic exists in exactly one
place.
"""

from dataclasses import dataclass, field

from app.strategy_builder.context import StrategyContext
from app.strategy_builder.models import DetectorReference, IndicatorReference, RuleReference

RULE_SECTIONS = ("filters", "entry_rules", "exit_rules")


@dataclass
class ResolvedComponents:
    """The outcome of resolving an SDL document's components against the registries."""

    indicators: list[IndicatorReference] = field(default_factory=list)
    detectors: list[DetectorReference] = field(default_factory=list)
    rules: list[RuleReference] = field(default_factory=list)
    missing_types: list[tuple[str, str]] = field(default_factory=list)  # (local_name, type)
    ambiguous_types: list[tuple[str, str]] = field(default_factory=list)  # (local_name, type)
    depends_on: dict[str, list[str]] = field(default_factory=dict)  # local_name -> [dependency local_names]

    def all_component_names(self) -> list[str]:
        """Every local name this resolution produced or attempted, including unresolved ones."""
        return (
            [ref.local_name for ref in self.indicators]
            + [ref.local_name for ref in self.detectors]
            + [ref.local_name for ref in self.rules]
            + [name for name, _ in self.missing_types]
            + [name for name, _ in self.ambiguous_types]
        )


def resolve_components(context: StrategyContext) -> ResolvedComponents:
    """Classify every SDL indicator/rule reference in `context.sdl_definition`."""
    sdl = context.sdl_definition
    resolved = ResolvedComponents()

    for spec in sdl.indicators:
        in_indicators = context.indicator_registry.is_registered(spec.type)
        in_detectors = context.smc_registry.is_registered(spec.type)
        if in_indicators and in_detectors:
            resolved.ambiguous_types.append((spec.name, spec.type))
        elif in_indicators:
            resolved.indicators.append(
                IndicatorReference.create(spec.name, spec.type, spec.params, spec.timeframe)
            )
        elif in_detectors:
            resolved.detectors.append(
                DetectorReference.create(spec.name, spec.type, spec.params, spec.timeframe)
            )
        else:
            resolved.missing_types.append((spec.name, spec.type))
        resolved.depends_on[spec.name] = list(spec.depends_on)

    for section in RULE_SECTIONS:
        for rule in getattr(sdl, section):
            resolved.rules.append(RuleReference(local_name=rule.name, section=section, condition=rule.condition))
            resolved.depends_on[rule.name] = list(rule.depends_on)

    return resolved
