"""Top-level facade for the Professional EA Generator Engine.

`EAGeneratorEngine` composes `EAGeneratorValidator`, `EAGenerator`,
`EAGeneratorStatisticsEngine`, and `EACompiler` (via `EAGeneratorRunner`)
into the single entrypoint most callers need. It consumes ONLY an
already-built `StrategyModel` (REQUIRED), plus optionally
already-completed `ValidationResult`/`OptimizationResult`/
`ResearchResult`/`PortfolioResult` outputs -- it never rebuilds any of
them. This engine is an OFFLINE CODE GENERATOR ONLY: it does not compile
MT5, execute trades, connect to a broker, call MetaTrader, run a Python
bridge, or call any external API. It only generates MQL5 source code.
Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.models import EAGeneratorConfiguration, EAGeneratorResult
from app.ea_generator.runner import EAGeneratorRunner, EAGeneratorSession
from app.optimization_engine.models import OptimizationResult
from app.portfolio_engine.models import PortfolioResult
from app.research_engine.models import ResearchResult
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger
from app.validation_engine.models import ValidationResult

logger = get_logger(__name__)


class EAGeneratorEngine(BaseEngine):
    """Generates a production-quality-skeleton MQL5 Expert Advisor from an
    already-validated `StrategyModel`.

    Consumes ONLY a `StrategyModel` (REQUIRED), plus optionally an
    already-completed `ValidationResult`/`OptimizationResult`/
    `ResearchResult`/`PortfolioResult` -- it never re-invokes Strategy
    Builder, Validation, Optimization, Research, or Portfolio logic; it
    only reads what they already produced. It NEVER compiles MT5, NEVER
    executes a trade, NEVER connects to a broker, and NEVER calls an
    external API -- only source-code generation.
    """

    name = "EAGeneratorEngine"

    def __init__(self, runner: EAGeneratorRunner | None = None) -> None:
        self._runner = runner or EAGeneratorRunner()

    def run(self, *args: Any, **kwargs: Any) -> EAGeneratorResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        strategy_model: StrategyModel,
        configuration: EAGeneratorConfiguration,
        validation_result: ValidationResult | None = None,
        optimization_result: OptimizationResult | None = None,
        research_result: ResearchResult | None = None,
        portfolio_result: PortfolioResult | None = None,
    ) -> EAGeneratorResult:
        """Generate one EA, raising on validation failure.

        Raises:
            EAValidationError: if the context fails pre-execution validation.
        """
        context = EAGeneratorContext(
            strategy_model=strategy_model,
            configuration=configuration,
            validation_result=validation_result,
            optimization_result=optimization_result,
            research_result=research_result,
            portfolio_result=portfolio_result,
        )
        return self._runner.execute(context)

    def try_execute(
        self,
        strategy_model: StrategyModel,
        configuration: EAGeneratorConfiguration,
        validation_result: ValidationResult | None = None,
        optimization_result: OptimizationResult | None = None,
        research_result: ResearchResult | None = None,
        portfolio_result: PortfolioResult | None = None,
    ) -> EAGeneratorSession:
        """Generate one EA. Never raises -- inspect the returned session."""
        context = EAGeneratorContext(
            strategy_model=strategy_model,
            configuration=configuration,
            validation_result=validation_result,
            optimization_result=optimization_result,
            research_result=research_result,
            portfolio_result=portfolio_result,
        )
        return self._runner.try_execute(context)
