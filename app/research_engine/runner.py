"""Orchestrates one full research run: validate, statistics, compare, rank,
analyze, derive insights, recommend, compile.

`ResearchRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `ResearchSession` is the outcome record of one run attempt,
mirroring `app.validation_engine.runner.ValidationRunner`'s "never raises,
inspect `.is_successful`" shape via `try_execute`, plus a raising
`execute()` for callers that prefer exceptions.

This runner never executes a trade, never optimizes, never replays a
chart, and never connects to a broker or MT5 -- every number it produces
comes from already-completed `StrategyModel`/`BacktestResult`/
`OptimizationResult`/`ValidationResult`/`ReplayResult` artifacts.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.base_engine import BaseEngine
from app.research_engine.analytics import AnalyticsEngine
from app.research_engine.comparison import ComparisonEngine
from app.research_engine.compiler import ResearchCompiler
from app.research_engine.context import ResearchContext
from app.research_engine.exceptions import ResearchValidationError
from app.research_engine.insights import InsightsEngine
from app.research_engine.models import ExecutiveSummary, ResearchResult
from app.research_engine.ranking import RankingEngine, ScoringEngine
from app.research_engine.recommendations import RecommendationEngine
from app.research_engine.statistics import ResearchStatisticsEngine
from app.research_engine.validator import ResearchCheckResult, ResearchValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ResearchSession:
    """The outcome record of one `ResearchRunner.try_execute()` call."""

    session_id: str
    context: ResearchContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ResearchCheckResult | None = None
    result: ResearchResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseResearchRunner(BaseEngine, ABC):
    """Common contract every research-running engine implements."""

    name = "BaseResearchRunner"

    @abstractmethod
    def execute(self, context: ResearchContext) -> ResearchResult:
        """Run a research analysis and return its `ResearchResult`.

        Raises:
            ResearchValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> ResearchResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class ResearchRunner(BaseResearchRunner):
    """The default `BaseResearchRunner` implementation."""

    name = "ResearchRunner"

    def __init__(
        self,
        validator: ResearchValidator | None = None,
        statistics_engine: ResearchStatisticsEngine | None = None,
        comparison_engine: ComparisonEngine | None = None,
        scoring_engine: ScoringEngine | None = None,
        ranking_engine: RankingEngine | None = None,
        analytics_engine: AnalyticsEngine | None = None,
        insights_engine: InsightsEngine | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        compiler: ResearchCompiler | None = None,
    ) -> None:
        self._validator = validator or ResearchValidator()
        self._statistics_engine = statistics_engine or ResearchStatisticsEngine()
        self._comparison_engine = comparison_engine or ComparisonEngine()
        self._scoring_engine = scoring_engine or ScoringEngine()
        self._ranking_engine = ranking_engine or RankingEngine()
        self._analytics_engine = analytics_engine or AnalyticsEngine()
        self._insights_engine = insights_engine or InsightsEngine()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._compiler = compiler or ResearchCompiler()

    def execute(self, context: ResearchContext) -> ResearchResult:
        """Run a research analysis, raising on validation failure.

        Raises:
            ResearchValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise ResearchValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: ResearchContext) -> ResearchSession:
        """Validate, compute statistics/ranking/analytics/insights/recommendations, and compile `context`. Never raises."""
        session = ResearchSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Research session %s failed validation.", session.session_id)
            return session

        statistics_by_id = {r.strategy_model.metadata.id: self._statistics_engine.compute(r) for r in context.records}
        statistics = self._comparison_engine.compare(tuple(statistics_by_id.values()))

        strategy_scores = {sid: self._scoring_engine.strategy_score(stat) for sid, stat in statistics_by_id.items()}
        records_by_id = {r.strategy_model.metadata.id: r for r in context.records}
        confidence_scores = {
            sid: self._scoring_engine.confidence_score(records_by_id[sid], stat, context.configuration) for sid, stat in statistics_by_id.items()
        }
        institutional_scores = {
            sid: self._scoring_engine.institutional_quality_score(stat, strategy_scores[sid], confidence_scores[sid], context.configuration)
            for sid, stat in statistics_by_id.items()
        }
        strategy_names = {sid: records_by_id[sid].strategy_model.metadata.name for sid in statistics_by_id}

        rankings = self._ranking_engine.rank(statistics, strategy_scores, confidence_scores, institutional_scores, strategy_names, context.configuration)

        analytics = self._analytics_engine.analyze(context.records)

        strategy_insights = tuple(
            self._insights_engine.derive(
                records_by_id[sid], statistics_by_id[sid], strategy_scores[sid], confidence_scores[sid], institutional_scores[sid], context.configuration
            )
            for sid in sorted(statistics_by_id)
        )
        insights_by_id = {i.strategy_id: i for i in strategy_insights}

        recommendations = self._recommendation_engine.generate(rankings, insights_by_id)

        executive_summary = self._build_executive_summary(rankings)

        result = self._compiler.compile(context, rankings, statistics, analytics, strategy_insights, recommendations, executive_summary)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Research session %s completed (%d strategy(ies)).", session.session_id, len(context.records))
        return session

    @staticmethod
    def _build_executive_summary(rankings) -> ExecutiveSummary:
        if not rankings:
            return ExecutiveSummary(total_strategies_analyzed=0, average_institutional_quality_score=0.0, institutional_grade_count=0)

        top = rankings[0]
        scores = [e.institutional_quality_score.score for e in rankings]
        institutional_count = sum(1 for e in rankings if e.institutional_quality_score.is_institutional_grade)

        key_findings = [
            f"{len(rankings)} strategy(ies) analyzed; top-ranked is '{top.strategy_name}' (score {top.institutional_quality_score.score:.1f}/100).",
            f"{institutional_count} of {len(rankings)} strategy(ies) meet the institutional-grade quality bar.",
        ]

        return ExecutiveSummary(
            total_strategies_analyzed=len(rankings),
            top_strategy_id=top.strategy_id,
            top_strategy_name=top.strategy_name,
            average_institutional_quality_score=round(sum(scores) / len(scores), 4),
            institutional_grade_count=institutional_count,
            key_findings=tuple(key_findings),
        )
