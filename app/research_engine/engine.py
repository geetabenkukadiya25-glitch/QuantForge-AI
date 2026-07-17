"""Top-level facade for the Research & Strategy Intelligence Engine.

`ResearchEngine` composes `ResearchValidator`, `ResearchCompiler`, and
`ResearchRunner` into the single entrypoint most callers need. It
consumes ONLY already-completed outputs from Strategy Builder,
Backtesting Engine, Optimization Engine, Validation Engine, and
(optionally, for visualization only) Replay Engine -- it never rebuilds
any of them. It NEVER executes trades, NEVER optimizes strategies,
NEVER replays charts, and NEVER connects to a broker or MT5. Implements
`BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.research_engine.context import ResearchContext, StrategyRecord
from app.research_engine.models import ResearchConfiguration, ResearchResult
from app.research_engine.runner import ResearchRunner, ResearchSession
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResearchEngine(BaseEngine):
    """Analyzes and compares already-completed strategy research results.

    Consumes ONLY `StrategyRecord`s -- immutable bundles of a
    `StrategyModel`, a `BacktestResult`, and optionally an
    `OptimizationResult`/`ValidationResult`/`ReplayResult`. It never
    re-invokes Strategy Builder, Backtesting, Optimization, Validation,
    or Replay logic; it only reads what they already produced.
    """

    name = "ResearchEngine"

    def __init__(self, runner: ResearchRunner | None = None) -> None:
        self._runner = runner or ResearchRunner()

    def run(self, *args: Any, **kwargs: Any) -> ResearchResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(self, records: tuple[StrategyRecord, ...], configuration: ResearchConfiguration) -> ResearchResult:
        """Run one research analysis, raising on validation failure.

        Raises:
            ResearchValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(ResearchContext(records=records, configuration=configuration))

    def try_execute(self, records: tuple[StrategyRecord, ...], configuration: ResearchConfiguration) -> ResearchSession:
        """Run one research analysis. Never raises -- inspect the returned session."""
        return self._runner.try_execute(ResearchContext(records=records, configuration=configuration))
