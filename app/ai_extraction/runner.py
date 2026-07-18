"""Orchestrates the full extraction pipeline: Document Loader -> Document
Parser -> Section Detection -> Strategy Analyzer -> Indicator Extractor ->
Smart Money Extractor -> Entry Rule Extractor -> Exit Rule Extractor ->
Risk Management Extractor -> Session Extractor -> Timeframe Extractor ->
Parameter Extractor -> Missing Information Detector -> SDL Generator ->
Validation -> Extraction Report.

`ExtractionRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `ExtractionSession` is the outcome record of one run
attempt, mirroring every other engine's "never raises, inspect
`.is_successful`" shape via `try_execute`, plus a raising `execute()` for
callers that prefer exceptions.

This runner never fetches external content, never calls an external AI
API, and never generates a trading idea -- every extracted item traces
back to text already present in the input, and the generated SDL is
always an explicit DRAFT requiring human review (see `models.py`'s
module docstring and `PROJECT_VISION.md`'s YouTube strategy workflow).
"""

import uuid
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.ai_extraction.analyzer import StrategyAnalyzer
from app.ai_extraction.compiler import ExtractionCompiler
from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.exceptions import ExtractionValidationError
from app.ai_extraction.extractors import (
    EntryRuleExtractor,
    ExitRuleExtractor,
    IndicatorExtractor,
    ParameterExtractor,
    RiskManagementExtractor,
    SessionExtractor,
    SmartMoneyExtractor,
    TimeframeExtractor,
)
from app.ai_extraction.loader import DocumentLoader
from app.ai_extraction.missing_info import MissingInformationDetector
from app.ai_extraction.models import CategoryConfidence, ConfidenceReport, ExtractionResult, SDLValidationSummary
from app.ai_extraction.parser import DocumentParser
from app.ai_extraction.sdl_generator import SDLGenerator
from app.ai_extraction.sections import SectionDetector
from app.ai_extraction.validator import ExtractionCheckResult, ExtractionValidator
from app.core.base_engine import BaseEngine
from app.sdl.validator import StrategyValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ExtractionSession:
    """The outcome record of one `ExtractionRunner.try_execute()` call."""

    session_id: str
    context: ExtractionContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ExtractionCheckResult | None = None
    result: ExtractionResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseExtractionRunner(BaseEngine, ABC):
    """Common contract every extraction-running engine implements."""

    name = "BaseExtractionRunner"

    @abstractmethod
    def execute(self, context: ExtractionContext) -> ExtractionResult:
        """Run an extraction and return its `ExtractionResult`.

        Raises:
            ExtractionValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> ExtractionResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class ExtractionRunner(BaseExtractionRunner):
    """The default `BaseExtractionRunner` implementation: runs the full 15-stage pipeline."""

    name = "ExtractionRunner"

    def __init__(
        self,
        validator: ExtractionValidator | None = None,
        loader: DocumentLoader | None = None,
        parser: DocumentParser | None = None,
        section_detector: SectionDetector | None = None,
        analyzer: StrategyAnalyzer | None = None,
        indicator_extractor: IndicatorExtractor | None = None,
        smart_money_extractor: SmartMoneyExtractor | None = None,
        entry_rule_extractor: EntryRuleExtractor | None = None,
        exit_rule_extractor: ExitRuleExtractor | None = None,
        risk_extractor: RiskManagementExtractor | None = None,
        session_extractor: SessionExtractor | None = None,
        timeframe_extractor: TimeframeExtractor | None = None,
        parameter_extractor: ParameterExtractor | None = None,
        missing_info_detector: MissingInformationDetector | None = None,
        sdl_generator: SDLGenerator | None = None,
        sdl_validator: StrategyValidator | None = None,
        compiler: ExtractionCompiler | None = None,
    ) -> None:
        self._validator = validator or ExtractionValidator()
        self._loader = loader or DocumentLoader()
        self._parser = parser or DocumentParser()
        self._section_detector = section_detector or SectionDetector()
        self._analyzer = analyzer or StrategyAnalyzer()
        self._indicator_extractor = indicator_extractor or IndicatorExtractor()
        self._smart_money_extractor = smart_money_extractor or SmartMoneyExtractor()
        self._entry_rule_extractor = entry_rule_extractor or EntryRuleExtractor()
        self._exit_rule_extractor = exit_rule_extractor or ExitRuleExtractor()
        self._risk_extractor = risk_extractor or RiskManagementExtractor()
        self._session_extractor = session_extractor or SessionExtractor()
        self._timeframe_extractor = timeframe_extractor or TimeframeExtractor()
        self._parameter_extractor = parameter_extractor or ParameterExtractor()
        self._missing_info_detector = missing_info_detector or MissingInformationDetector()
        self._sdl_generator = sdl_generator or SDLGenerator()
        self._sdl_validator = sdl_validator or StrategyValidator()
        self._compiler = compiler or ExtractionCompiler()

    def execute(self, context: ExtractionContext) -> ExtractionResult:
        """Run an extraction, raising on validation failure.

        Raises:
            ExtractionValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise ExtractionValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: ExtractionContext) -> ExtractionSession:
        """Run the full extraction pipeline over `context`. Never raises."""
        session = ExtractionSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Extraction session %s failed validation.", session.session_id)
            return session

        max_snippet = context.configuration.max_snippet_length

        # Document Loader -> Document Parser -> Section Detection
        document_content = self._loader.load(context.raw_text, context.source_type)
        parsed = self._parser.parse(document_content.normalized_text)
        sections = self._section_detector.detect(parsed)

        # Strategy Analyzer
        overview = self._analyzer.analyze(parsed)
        if context.configuration.strategy_name_hint:
            overview = type(overview)(name=context.configuration.strategy_name_hint, description=overview.description, name_detected=True, description_detected=overview.description_detected)

        # Indicator Extractor / Smart Money Extractor
        indicators = self._indicator_extractor.extract(parsed.lines, context.indicator_registry, max_snippet)
        detectors = self._smart_money_extractor.extract(parsed.lines, context.smc_registry, max_snippet)
        unknown_items = (
            *self._indicator_extractor.unknown_items(sections, context.indicator_registry),
            *self._smart_money_extractor.unknown_items(sections, context.smc_registry),
        )

        # Entry Rule Extractor / Exit Rule Extractor
        entry_rules = self._entry_rule_extractor.extract(parsed.lines, sections, max_snippet)
        exit_rules = self._exit_rule_extractor.extract(parsed.lines, sections, max_snippet)

        # Risk Management Extractor
        risk_mentions = self._risk_extractor.extract(parsed.lines, max_snippet)

        # Session Extractor / Timeframe Extractor
        sessions = self._session_extractor.extract(parsed.lines, max_snippet)
        timeframes = self._timeframe_extractor.extract(parsed.lines, max_snippet)

        # Parameter Extractor
        parameters = self._parameter_extractor.extract(indicators, parsed.lines, max_snippet)

        # Missing Information Detector
        missing_information = self._missing_info_detector.detect(
            indicators, detectors, entry_rules, exit_rules, risk_mentions, sessions, timeframes,
            overview.name_detected, overview.description_detected,
        )

        confidence = self._build_confidence_report(indicators, detectors, entry_rules, exit_rules, risk_mentions, sessions, timeframes)

        # SDL Generator
        draft = self._sdl_generator.generate(overview, indicators, detectors, entry_rules, exit_rules, risk_mentions, sessions, timeframes)
        generated_sdl_yaml = yaml.safe_dump(draft.model_dump(mode="json"), sort_keys=False, allow_unicode=True)

        # Validation (reuses the real, existing app.sdl.StrategyValidator -- never reimplemented)
        sdl_validation_result = self._sdl_validator.validate(draft)
        sdl_validation = SDLValidationSummary(
            is_valid=sdl_validation_result.is_valid,
            errors=tuple(str(issue) for issue in sdl_validation_result.errors),
            warnings=tuple(str(issue) for issue in sdl_validation_result.warnings),
        )

        # Extraction Report (the compiled ExtractionResult itself; presentation views live in report.py)
        result = self._compiler.compile(
            context, overview.name, overview.description, indicators, detectors, sessions, timeframes,
            entry_rules, exit_rules, risk_mentions, parameters, unknown_items, confidence, missing_information,
            generated_sdl_yaml, sdl_validation,
        )

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Extraction session %s completed ('%s').", session.session_id, overview.name)
        return session

    @staticmethod
    def _build_confidence_report(indicators, detectors, entry_rules, exit_rules, risk_mentions, sessions, timeframes) -> ConfidenceReport:
        categories: list[CategoryConfidence] = []
        for label, mentions in (
            ("indicators", indicators), ("detectors", detectors), ("entry_rules", entry_rules), ("exit_rules", exit_rules),
            ("risk", risk_mentions), ("sessions", sessions), ("timeframes", timeframes),
        ):
            if not mentions:
                continue
            average = sum(m.confidence for m in mentions) / len(mentions)
            categories.append(CategoryConfidence(category=label, score=round(average, 4), item_count=len(mentions)))

        overall = round(sum(c.score for c in categories) / len(categories), 4) if categories else 0.0
        return ConfidenceReport(overall_confidence=overall, category_confidences=tuple(categories))
