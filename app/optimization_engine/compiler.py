"""Compiles a completed search into an immutable `OptimizationResult`.

A pure transformation: given an `OptimizationContext` and the
already-computed candidates/history/statistics, build the final
`OptimizationResult` and its content checksum -- the same discipline
`BacktestCompiler`/`StrategyCompiler` established: every identity/
timestamp field is excluded from the checksum payload before hashing, so
two runs of the same context produce the same checksum.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.optimization_engine.context import OptimizationContext
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION, OptimizationMetadata
from app.optimization_engine.models import OptimizationCandidate, OptimizationHistory, OptimizationResult, OptimizationStatistics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizationCompiler:
    """Builds an `OptimizationResult` from one run's candidates, history, and statistics."""

    def compile(
        self,
        context: OptimizationContext,
        candidates: tuple[OptimizationCandidate, ...],
        history: OptimizationHistory,
        statistics: OptimizationStatistics,
    ) -> OptimizationResult:
        base_model = context.base_strategy_model
        metadata = OptimizationMetadata(
            optimization_id=str(uuid.uuid4()),
            strategy_id=base_model.metadata.id,
            base_strategy_model_id=base_model.model_id,
            base_strategy_checksum=base_model.checksum,
            strategy_model_version=base_model.metadata.model_version,
            result_version=OPTIMIZATION_RESULT_VERSION,
        )

        checksum = self._checksum(
            metadata=metadata,
            configuration=context.configuration,
            parameter_space=context.parameter_space,
            candidates=candidates,
            history=history,
            statistics=statistics,
        )

        result = OptimizationResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            parameter_space=context.parameter_space,
            candidates=candidates,
            history=history,
            statistics=statistics,
            best_candidate_id=statistics.best_candidate_id,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Compiled optimization run for strategy '%s' (checksum=%s, %d candidate(s))",
            metadata.strategy_id,
            checksum[:12],
            len(candidates),
        )
        return result

    @staticmethod
    def _checksum(metadata, configuration, parameter_space, candidates, history, statistics) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.optimization_id`) -- two runs of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["optimization_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "parameter_space": parameter_space.model_dump(mode="json"),
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "history": history.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
