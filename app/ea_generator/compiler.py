"""Compiles a completed EA generation into an immutable `EAGeneratorResult`.

A pure transformation: given an `EAGeneratorContext` and every already-
generated artifact (source code, inputs, indicator declarations, risk
parameters, trade management, statistics), build the final
`EAGeneratorResult` and its content checksum -- the same discipline
every prior compiler in this platform established: every identity/
timestamp field is excluded from the checksum payload before hashing,
so two generations over the same context produce the same checksum
(the generated `source_code` text itself IS part of the payload, so
"same input = identical EA source = identical checksum" holds by
construction). Uses the shared `app.core.checksums` helper.
"""

import uuid
from datetime import datetime, timezone

from app.core.checksums import compute_checksum
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.metadata import EA_RESULT_VERSION, EAGeneratorMetadata
from app.ea_generator.models import (
    EAGeneratorResult,
    EAGeneratorStatistics,
    GeneratedIndicatorDeclaration,
    GeneratedInput,
    GeneratedRiskParameters,
    GeneratedTradeManagement,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EACompiler:
    """Builds an `EAGeneratorResult` from one generation's computed artifacts."""

    def compile(
        self,
        context: EAGeneratorContext,
        source_code: str,
        inputs: tuple[GeneratedInput, ...],
        indicator_declarations: tuple[GeneratedIndicatorDeclaration, ...],
        risk_parameters: GeneratedRiskParameters,
        trade_management: GeneratedTradeManagement,
        statistics: EAGeneratorStatistics,
    ) -> EAGeneratorResult:
        strategy_model = context.strategy_model
        metadata = EAGeneratorMetadata(
            ea_id=str(uuid.uuid4()),
            strategy_id=strategy_model.metadata.id,
            strategy_checksum=strategy_model.checksum,
            output_filename=context.configuration.output_filename,
            result_version=EA_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, source_code, inputs, indicator_declarations, risk_parameters, trade_management, statistics)

        result = EAGeneratorResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            source_code=source_code,
            inputs=inputs,
            indicator_declarations=indicator_declarations,
            risk_parameters=risk_parameters,
            trade_management=trade_management,
            statistics=statistics,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled EA for strategy %r (checksum=%s)", strategy_model.metadata.id, checksum[:12])
        return result

    @staticmethod
    def _checksum(
        metadata: EAGeneratorMetadata,
        configuration,
        source_code: str,
        inputs: tuple[GeneratedInput, ...],
        indicator_declarations: tuple[GeneratedIndicatorDeclaration, ...],
        risk_parameters: GeneratedRiskParameters,
        trade_management: GeneratedTradeManagement,
        statistics: EAGeneratorStatistics,
    ) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.ea_id`) -- two generations of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["ea_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "source_code": source_code,
            "inputs": [i.model_dump(mode="json") for i in inputs],
            "indicator_declarations": [d.model_dump(mode="json") for d in indicator_declarations],
            "risk_parameters": risk_parameters.model_dump(mode="json"),
            "trade_management": trade_management.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
        }
        return compute_checksum(payload)
