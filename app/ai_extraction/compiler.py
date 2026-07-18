"""Compiles a completed extraction run into an immutable `ExtractionResult`.

A pure transformation: given the context and every already-computed
pipeline artifact, build the final `ExtractionResult` and its content
checksum -- the same discipline every prior compiler in this platform
established: every identity/timestamp field is excluded from the
checksum payload before hashing, so two runs of the same input text
produce the same checksum.
"""

import uuid
from datetime import datetime, timezone

from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.metadata import EXTRACTION_RESULT_VERSION, ExtractionMetadata
from app.ai_extraction.models import (
    ConfidenceReport,
    DetectorMention,
    ExtractionResult,
    IndicatorMention,
    MissingInformationReport,
    ParameterMention,
    RiskMention,
    RuleMention,
    SDLValidationSummary,
    SessionMention,
    TimeframeMention,
)
from app.core.checksums import compute_checksum, sha256_hex
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExtractionCompiler:
    """Builds an `ExtractionResult` from one run's computed pipeline artifacts."""

    def compile(
        self,
        context: ExtractionContext,
        strategy_name: str,
        description: str,
        indicators: tuple[IndicatorMention, ...],
        detectors: tuple[DetectorMention, ...],
        sessions: tuple[SessionMention, ...],
        timeframes: tuple[TimeframeMention, ...],
        entry_rules: tuple[RuleMention, ...],
        exit_rules: tuple[RuleMention, ...],
        risk_mentions: tuple[RiskMention, ...],
        parameters: tuple[ParameterMention, ...],
        unknown_items: tuple[str, ...],
        confidence: ConfidenceReport,
        missing_information: MissingInformationReport,
        generated_sdl_yaml: str,
        sdl_validation: SDLValidationSummary,
    ) -> ExtractionResult:
        metadata = ExtractionMetadata(
            extraction_id=str(uuid.uuid4()),
            source_type=context.source_type.value,
            source_checksum=sha256_hex(context.raw_text),
            result_version=EXTRACTION_RESULT_VERSION,
        )

        checksum = self._checksum(
            metadata, context.configuration, strategy_name, description, indicators, detectors, sessions, timeframes,
            entry_rules, exit_rules, risk_mentions, parameters, unknown_items, confidence, missing_information,
            generated_sdl_yaml, sdl_validation,
        )

        result = ExtractionResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            strategy_name=strategy_name,
            description=description,
            indicators=indicators,
            detectors=detectors,
            sessions=sessions,
            timeframes=timeframes,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            risk_mentions=risk_mentions,
            parameters=parameters,
            unknown_items=unknown_items,
            confidence=confidence,
            missing_information=missing_information,
            generated_sdl_yaml=generated_sdl_yaml,
            sdl_validation=sdl_validation,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled extraction '%s' (checksum=%s)", strategy_name, checksum[:12])
        return result

    @staticmethod
    def _checksum(metadata, configuration, strategy_name, description, indicators, detectors, sessions, timeframes, entry_rules, exit_rules, risk_mentions, parameters, unknown_items, confidence, missing_information, generated_sdl_yaml, sdl_validation) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.extraction_id`) -- two runs of
        the same input text produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["extraction_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "strategy_name": strategy_name,
            "description": description,
            "indicators": [m.model_dump(mode="json") for m in indicators],
            "detectors": [m.model_dump(mode="json") for m in detectors],
            "sessions": [m.model_dump(mode="json") for m in sessions],
            "timeframes": [m.model_dump(mode="json") for m in timeframes],
            "entry_rules": [m.model_dump(mode="json") for m in entry_rules],
            "exit_rules": [m.model_dump(mode="json") for m in exit_rules],
            "risk_mentions": [m.model_dump(mode="json") for m in risk_mentions],
            "parameters": [m.model_dump(mode="json") for m in parameters],
            "unknown_items": list(unknown_items),
            "confidence": confidence.model_dump(mode="json"),
            "missing_information": missing_information.model_dump(mode="json"),
            "generated_sdl_yaml": generated_sdl_yaml,
            "sdl_validation": sdl_validation.model_dump(mode="json"),
        }
        return compute_checksum(payload)
