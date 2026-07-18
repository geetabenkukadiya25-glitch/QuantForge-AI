"""Top-level facade for the Professional Portfolio Management Engine.

`PortfolioManagementEngine` composes `PortfolioValidator`,
`PortfolioCompiler`, and `PortfolioRunner` into the single entrypoint
most callers need. It consumes ONLY already-completed outputs from
Strategy Builder and the Backtesting Engine (both required), plus
optionally the Optimization Engine, Validation Engine, Replay Engine,
and Research Engine -- it never rebuilds any of them. It NEVER executes
trades, NEVER connects to a broker or MT5, NEVER optimizes, and NEVER
validates. Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.portfolio_engine.context import PortfolioContext, PortfolioStrategyEntry
from app.portfolio_engine.models import PortfolioConfiguration, PortfolioResult
from app.portfolio_engine.runner import PortfolioRunner, PortfolioSession
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioManagementEngine(BaseEngine):
    """Analyzes and manages a portfolio of already-completed strategy results.

    Consumes ONLY `PortfolioStrategyEntry`s -- immutable bundles of a
    `StrategyModel`, a `BacktestResult`, and optionally an
    `OptimizationResult`/`ValidationResult`/`ReplayResult`/`ResearchResult`.
    It never re-invokes Strategy Builder, Backtesting, Optimization,
    Validation, Replay, or Research logic; it only reads what they
    already produced. Only aggregation -- never trading, never a broker,
    never MT5.
    """

    name = "PortfolioManagementEngine"

    def __init__(self, runner: PortfolioRunner | None = None) -> None:
        self._runner = runner or PortfolioRunner()

    def run(self, *args: Any, **kwargs: Any) -> PortfolioResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(self, entries: tuple[PortfolioStrategyEntry, ...], configuration: PortfolioConfiguration) -> PortfolioResult:
        """Build one portfolio, raising on validation failure.

        Raises:
            PortfolioValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(PortfolioContext(entries=entries, configuration=configuration))

    def try_execute(self, entries: tuple[PortfolioStrategyEntry, ...], configuration: PortfolioConfiguration) -> PortfolioSession:
        """Build one portfolio. Never raises -- inspect the returned session."""
        return self._runner.try_execute(PortfolioContext(entries=entries, configuration=configuration))
