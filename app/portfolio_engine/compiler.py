"""Compiles a completed portfolio build into an immutable `PortfolioResult`.

A pure transformation: given a `PortfolioContext` and every already-
computed allocation/statistics/correlation/exposure/ranking/analytics
artifact, build the final `PortfolioResult` and its content checksum --
the same discipline every prior compiler in this platform established:
every identity/timestamp field is excluded from the checksum payload
before hashing, so two builds of the same context produce the same
checksum. Uses the shared `app.core.checksums` helper, the same
canonicalization every other engine's compiler now delegates to.
"""

import uuid
from datetime import datetime, timezone

from app.core.checksums import compute_checksum
from app.portfolio_engine.context import PortfolioContext
from app.portfolio_engine.metadata import PORTFOLIO_RESULT_VERSION, PortfolioMetadata
from app.portfolio_engine.models import (
    AllocationBreakdown,
    CorrelationMatrix,
    ExposureReport,
    PortfolioAnalytics,
    PortfolioExecutiveSummary,
    PortfolioRanking,
    PortfolioResult,
    PortfolioStatistics,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioCompiler:
    """Builds a `PortfolioResult` from one build's computed pipeline artifacts."""

    def compile(
        self,
        context: PortfolioContext,
        allocation: AllocationBreakdown,
        statistics: PortfolioStatistics,
        correlation_matrix: CorrelationMatrix,
        exposure: ExposureReport,
        ranking: PortfolioRanking,
        analytics: PortfolioAnalytics,
        executive_summary: PortfolioExecutiveSummary,
    ) -> PortfolioResult:
        # Sorted by strategy_id (not `context.entries`' input order) so the
        # checksum -- and this metadata -- stay independent of the order
        # entries were supplied in.
        ordered_entries = sorted(context.entries, key=lambda e: e.strategy_model.metadata.id)
        metadata = PortfolioMetadata(
            portfolio_id=str(uuid.uuid4()),
            strategy_ids=tuple(e.strategy_model.metadata.id for e in ordered_entries),
            strategy_checksums=tuple(e.strategy_model.checksum for e in ordered_entries),
            backtest_result_ids=tuple(e.backtest_result.result_id for e in ordered_entries),
            result_version=PORTFOLIO_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, allocation, statistics, correlation_matrix, exposure, ranking, analytics, executive_summary)

        result = PortfolioResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            allocation=allocation,
            statistics=statistics,
            correlation_matrix=correlation_matrix,
            exposure=exposure,
            ranking=ranking,
            analytics=analytics,
            executive_summary=executive_summary,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled portfolio (%d strategy(ies), checksum=%s)", len(ordered_entries), checksum[:12])
        return result

    @staticmethod
    def _checksum(
        metadata: PortfolioMetadata,
        configuration,
        allocation: AllocationBreakdown,
        statistics: PortfolioStatistics,
        correlation_matrix: CorrelationMatrix,
        exposure: ExposureReport,
        ranking: PortfolioRanking,
        analytics: PortfolioAnalytics,
        executive_summary: PortfolioExecutiveSummary,
    ) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.portfolio_id`) -- two builds of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["portfolio_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "allocation": allocation.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
            "correlation_matrix": correlation_matrix.model_dump(mode="json"),
            "exposure": exposure.model_dump(mode="json"),
            "ranking": ranking.model_dump(mode="json"),
            "analytics": analytics.model_dump(mode="json"),
            "executive_summary": executive_summary.model_dump(mode="json"),
        }
        return compute_checksum(payload)
