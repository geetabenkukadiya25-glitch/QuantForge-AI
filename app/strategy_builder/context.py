"""The standardized input the Strategy Builder consumes.

`StrategyContext` bundles exactly the four sanctioned input sources for
this phase: an SDL `StrategyDefinition`, and the `IndicatorRegistry`/
`SMCRegistry` needed to resolve the names it references. It never
carries execution logic or broker APIs.
"""

from dataclasses import dataclass

from app.indicator_engine.registry import IndicatorRegistry
from app.sdl.models import StrategyDefinition
from app.smart_money_engine.registry import SMCRegistry


@dataclass(frozen=True)
class StrategyContext:
    """Immutable wrapper around the SDL document and the registries used to resolve it."""

    sdl_definition: StrategyDefinition
    indicator_registry: IndicatorRegistry
    smc_registry: SMCRegistry
