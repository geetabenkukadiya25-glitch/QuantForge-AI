"""Compiles a completed validation run into an immutable `ValidationResult`.

A pure transformation: given a `ValidationContext`, the resolved
candidate, and the already-computed walk-forward/Monte Carlo/analysis
artifacts, build the final `ValidationResult` and its content checksum --
the same discipline `OptimizationCompiler`/`BacktestCompiler` established:
every identity/timestamp field is excluded from the checksum payload
before hashing, so two runs of the same context produce the same checksum.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.validation_engine.context import ValidationContext
from app.validation_engine.metadata import VALIDATION_RESULT_VERSION, ValidationMetadata
from app.validation_engine.models import ConfidenceScore, MonteCarloResult, RobustnessScore, StabilityScore, ValidationResult, WalkForwardResult
from app.validation_engine.resolve import ResolvedCandidate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationCompiler:
    """Builds a `ValidationResult` from one run's resolved candidate and computed artifacts."""

    def compile(
        self,
        context: ValidationContext,
        resolved: ResolvedCandidate,
        walk_forward_result: WalkForwardResult | None,
        monte_carlo_result: MonteCarloResult | None,
        robustness_score: RobustnessScore | None,
        confidence_score: ConfidenceScore | None,
        stability_score: StabilityScore | None,
    ) -> ValidationResult:
        metadata = ValidationMetadata(
            validation_id=str(uuid.uuid4()),
            strategy_id=context.base_strategy_model.metadata.id,
            optimization_result_id=context.optimization_result.result_id,
            optimization_checksum=context.optimization_result.checksum,
            candidate_id=resolved.outcome.candidate_id,
            strategy_model_checksum=resolved.strategy_model.checksum,
            result_version=VALIDATION_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, walk_forward_result, monte_carlo_result, robustness_score, confidence_score, stability_score)

        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            walk_forward_result=walk_forward_result,
            monte_carlo_result=monte_carlo_result,
            robustness_score=robustness_score,
            confidence_score=confidence_score,
            stability_score=stability_score,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled validation run for strategy '%s' (checksum=%s)", metadata.strategy_id, checksum[:12])
        return result

    @staticmethod
    def _checksum(metadata, configuration, walk_forward_result, monte_carlo_result, robustness_score, confidence_score, stability_score) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.validation_id`) -- two runs of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["validation_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "walk_forward_result": walk_forward_result.model_dump(mode="json") if walk_forward_result else None,
            "monte_carlo_result": monte_carlo_result.model_dump(mode="json") if monte_carlo_result else None,
            "robustness_score": robustness_score.model_dump(mode="json") if robustness_score else None,
            "confidence_score": confidence_score.model_dump(mode="json") if confidence_score else None,
            "stability_score": stability_score.model_dump(mode="json") if stability_score else None,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
