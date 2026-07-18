"""Orchestrates one full portfolio build: validate, allocate, aggregate
statistics/correlation/exposure/ranking/analytics, compile.

`PortfolioRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `PortfolioSession` is the outcome record of one build
attempt, mirroring `app.research_engine.runner.ResearchRunner`'s "never
raises, inspect `.is_successful`" shape via `try_execute`, plus a raising
`execute()` for callers that prefer exceptions.

This runner never trades, never connects to a broker or MT5, never
optimizes, never validates, and never replays a chart -- every number it
produces comes from already-completed `StrategyModel`/`BacktestResult`/
`OptimizationResult`/`ValidationResult`/`ReplayResult`/`ResearchResult`
artifacts.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.base_engine import BaseEngine
from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.analytics import AnalyticsEngine
from app.portfolio_engine.compiler import PortfolioCompiler
from app.portfolio_engine.context import PortfolioContext
from app.portfolio_engine.correlation import CorrelationEngine
from app.portfolio_engine.exceptions import PortfolioValidationError
from app.portfolio_engine.models import PortfolioExecutiveSummary, PortfolioResult
from app.portfolio_engine.ranking import RankingEngine
from app.portfolio_engine.risk import RiskEngine
from app.portfolio_engine.statistics import PortfolioStatisticsEngine
from app.portfolio_engine.validator import PortfolioCheckResult, PortfolioValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class PortfolioSession:
    """The outcome record of one `PortfolioRunner.try_execute()` call."""

    session_id: str
    context: PortfolioContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: PortfolioCheckResult | None = None
    result: PortfolioResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BasePortfolioRunner(BaseEngine, ABC):
    """Common contract every portfolio-building engine implements."""

    name = "BasePortfolioRunner"

    @abstractmethod
    def execute(self, context: PortfolioContext) -> PortfolioResult:
        """Build a portfolio and return its `PortfolioResult`.

        Raises:
            PortfolioValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> PortfolioResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class PortfolioRunner(BasePortfolioRunner):
    """The default `BasePortfolioRunner` implementation."""

    name = "PortfolioRunner"

    def __init__(
        self,
        validator: PortfolioValidator | None = None,
        allocation_engine: AllocationEngine | None = None,
        risk_engine: RiskEngine | None = None,
        statistics_engine: PortfolioStatisticsEngine | None = None,
        correlation_engine: CorrelationEngine | None = None,
        ranking_engine: RankingEngine | None = None,
        analytics_engine: AnalyticsEngine | None = None,
        compiler: PortfolioCompiler | None = None,
    ) -> None:
        self._validator = validator or PortfolioValidator()
        self._allocation_engine = allocation_engine or AllocationEngine()
        self._risk_engine = risk_engine or RiskEngine()
        self._statistics_engine = statistics_engine or PortfolioStatisticsEngine()
        self._correlation_engine = correlation_engine or CorrelationEngine()
        self._ranking_engine = ranking_engine or RankingEngine()
        self._analytics_engine = analytics_engine or AnalyticsEngine()
        self._compiler = compiler or PortfolioCompiler()

    def execute(self, context: PortfolioContext) -> PortfolioResult:
        """Build a portfolio, raising on validation failure.

        Raises:
            PortfolioValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise PortfolioValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: PortfolioContext) -> PortfolioSession:
        """Validate, allocate, aggregate, and compile `context`. Never raises."""
        session = PortfolioSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Portfolio session %s failed validation.", session.session_id)
            return session

        entries = context.entries
        weights = self._allocation_engine.resolve_weights(entries, context.configuration)

        risk_contribution = self._risk_engine.risk_contribution_pct(entries, weights)
        allocation = self._allocation_engine.allocate(entries, context.configuration, risk_contribution)

        portfolio_max_drawdown_pct = self._risk_engine.portfolio_max_drawdown_pct(entries, weights)
        statistics = self._statistics_engine.compute(entries, weights, portfolio_max_drawdown_pct)

        correlation_matrix = self._correlation_engine.correlate(entries)
        exposure = self._correlation_engine.exposure(entries, weights)

        ranking = self._ranking_engine.rank(entries)

        risk_score = self._risk_engine.risk_score(portfolio_max_drawdown_pct, correlation_matrix.average_correlation)
        analytics = self._analytics_engine.analyze(entries, weights, correlation_matrix, statistics, risk_score)

        executive_summary = self._build_executive_summary(entries, statistics, analytics, allocation)

        result = self._compiler.compile(context, allocation, statistics, correlation_matrix, exposure, ranking, analytics, executive_summary)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Portfolio session %s completed (%d strategy(ies)).", session.session_id, len(entries))
        return session

    @staticmethod
    def _build_executive_summary(entries, statistics, analytics, allocation) -> PortfolioExecutiveSummary:
        if not entries:
            return PortfolioExecutiveSummary(total_strategies=0, total_net_profit=0.0, portfolio_quality_score=0.0)

        top_allocation = max(allocation.strategy_allocations, key=lambda a: a.weight) if allocation.strategy_allocations else None

        key_findings = [
            f"{statistics.total_strategies} strategy(ies) combined; combined net profit {statistics.total_net_profit:.2f}.",
            f"Portfolio quality score {analytics.portfolio_quality_score:.1f}/100 (diversification {analytics.diversification_score:.1f}, risk {analytics.risk_score:.1f}).",
        ]

        return PortfolioExecutiveSummary(
            total_strategies=statistics.total_strategies,
            total_net_profit=statistics.total_net_profit,
            portfolio_quality_score=analytics.portfolio_quality_score,
            top_strategy_id=top_allocation.strategy_id if top_allocation else None,
            top_strategy_name=top_allocation.strategy_name if top_allocation else None,
            key_findings=tuple(key_findings),
        )
