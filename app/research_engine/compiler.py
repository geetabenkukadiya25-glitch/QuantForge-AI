"""Compiles a completed research run into an immutable `ResearchResult`.

A pure transformation: given a `ResearchContext` and the already-computed
rankings/statistics/analytics/insights/recommendations/executive summary,
build the final `ResearchResult` and its content checksum -- the same
discipline `ValidationCompiler`/`OptimizationCompiler`/`BacktestCompiler`
established: every identity/timestamp field is excluded from the
checksum payload before hashing, so two runs of the same context produce
the same checksum.
"""

import uuid
from datetime import datetime, timezone

from app.core.checksums import compute_checksum
from app.research_engine.context import ResearchContext
from app.research_engine.metadata import RESEARCH_RESULT_VERSION, ResearchMetadata
from app.research_engine.models import (
    ExecutiveSummary,
    Recommendation,
    ResearchAnalytics,
    ResearchResult,
    RankingEntry,
    ComparisonStatistics,
    StrategyInsights,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResearchCompiler:
    """Builds a `ResearchResult` from one run's computed artifacts."""

    def compile(
        self,
        context: ResearchContext,
        rankings: tuple[RankingEntry, ...],
        statistics: tuple[ComparisonStatistics, ...],
        analytics: ResearchAnalytics,
        strategy_insights: tuple[StrategyInsights, ...],
        recommendations: tuple[Recommendation, ...],
        executive_summary: ExecutiveSummary,
    ) -> ResearchResult:
        # Sorted by strategy_id (not `context.records`' input order) so the
        # checksum -- and this metadata -- stay independent of the order
        # records were supplied in, consistent with every other tuple this
        # engine produces (statistics, analytics, rankings are all sorted).
        ordered_records = sorted(context.records, key=lambda r: r.strategy_model.metadata.id)
        metadata = ResearchMetadata(
            research_id=str(uuid.uuid4()),
            strategy_ids=tuple(r.strategy_model.metadata.id for r in ordered_records),
            strategy_checksums=tuple(r.strategy_model.checksum for r in ordered_records),
            backtest_result_ids=tuple(r.backtest_result.result_id for r in ordered_records),
            result_version=RESEARCH_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, rankings, statistics, analytics, strategy_insights, recommendations, executive_summary)

        result = ResearchResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            rankings=rankings,
            statistics=statistics,
            analytics=analytics,
            strategy_insights=strategy_insights,
            recommendations=recommendations,
            executive_summary=executive_summary,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled research run over %d strategy(ies) (checksum=%s)", len(context.records), checksum[:12])
        return result

    @staticmethod
    def _checksum(metadata, configuration, rankings, statistics, analytics, strategy_insights, recommendations, executive_summary) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.research_id`) -- two runs of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["research_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "rankings": [r.model_dump(mode="json") for r in rankings],
            "statistics": [s.model_dump(mode="json") for s in statistics],
            "analytics": analytics.model_dump(mode="json"),
            "strategy_insights": [s.model_dump(mode="json") for s in strategy_insights],
            "recommendations": [r.model_dump(mode="json") for r in recommendations],
            "executive_summary": executive_summary.model_dump(mode="json"),
        }
        return compute_checksum(payload)
