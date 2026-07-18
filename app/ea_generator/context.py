"""The standardized input the EA Generator Engine consumes.

`EAGeneratorContext` bundles exactly the sanctioned input sources for
this engine: an already-built `StrategyModel` (REQUIRED), plus
optionally already-completed `ValidationResult`/`OptimizationResult`/
`ResearchResult`/`PortfolioResult` outputs (consumed only to enrich
generated comments/inputs, never re-invoked). The EA Generator never
rebuilds any of them, never trades, never optimizes, never validates,
never connects to a broker or MT5, and never compiles MQL5 -- it only
reads what already exists and emits source code.
"""

from dataclasses import dataclass

from app.ea_generator.models import EAGeneratorConfiguration
from app.optimization_engine.models import OptimizationResult
from app.portfolio_engine.models import PortfolioResult
from app.research_engine.models import ResearchResult
from app.strategy_builder.models import StrategyModel
from app.validation_engine.models import ValidationResult


@dataclass(frozen=True)
class EAGeneratorContext:
    """Immutable wrapper around one EA generation's inputs.

    `strategy_model` is REQUIRED -- every other engine's output is
    optional and only enriches the generated header comments and
    optimized `input` declarations when present.
    """

    strategy_model: StrategyModel
    configuration: EAGeneratorConfiguration
    validation_result: ValidationResult | None = None
    optimization_result: OptimizationResult | None = None
    research_result: ResearchResult | None = None
    portfolio_result: PortfolioResult | None = None
