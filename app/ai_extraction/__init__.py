"""AI Strategy Extraction Engine.

Converts external strategy document text (YouTube transcript, PDF,
Markdown, plain text, Pine Script, MQL4, MQL5, EasyLanguage, pseudocode,
OCR text) into a draft SDL document, a confidence report, and a
missing-information report. This engine is a deterministic, offline,
pattern/keyword-matching pipeline -- NOT a generative AI model, and it
NEVER calls an external API or network service (per "No External APIs").
It MUST NOT generate trading ideas; it only extracts information already
present in the supplied text, and every output is an explicit DRAFT
requiring human review, per `PROJECT_VISION.md`'s "AI assists, humans
approve" principle and its YouTube strategy workflow.
"""

from app.ai_extraction.analyzer import StrategyAnalyzer, StrategyOverview
from app.ai_extraction.compiler import ExtractionCompiler
from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.engine import AIStrategyExtractionEngine
from app.ai_extraction.exceptions import (
    ExtractionConfigurationError,
    ExtractionDisabledError,
    ExtractionEngineError,
    ExtractionExecutionError,
    ExtractionNotFoundError,
    ExtractionRegistrationError,
    ExtractionValidationError,
)
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
from app.ai_extraction.metadata import EXTRACTION_RESULT_VERSION, ExtractionMetadata
from app.ai_extraction.missing_info import MissingInformationDetector
from app.ai_extraction.models import (
    CategoryConfidence,
    ConfidenceReport,
    DetectedSection,
    DetectorMention,
    DocumentContent,
    ExtractionConfiguration,
    ExtractionResult,
    ExtractionWarning,
    IndicatorMention,
    MissingInformationReport,
    ParameterMention,
    RiskMention,
    RuleMention,
    SDLValidationSummary,
    SessionMention,
    SourceType,
    TimeframeMention,
)
from app.ai_extraction.parser import DocumentParser, ParsedDocument
from app.ai_extraction.registry import ExtractionRegistry
from app.ai_extraction.report import ExtractionReport
from app.ai_extraction.runner import BaseExtractionRunner, ExtractionRunner, ExtractionSession, SessionStatus
from app.ai_extraction.sdl_generator import SDLGenerator
from app.ai_extraction.sections import SectionDetector
from app.ai_extraction.serializer import ExtractionSerializer
from app.ai_extraction.validator import ExtractionCheckResult, ExtractionIssue, ExtractionValidator

__all__ = [
    "AIStrategyExtractionEngine",
    "ExtractionRunner",
    "BaseExtractionRunner",
    "ExtractionSession",
    "SessionStatus",
    "ExtractionContext",
    "ExtractionCompiler",
    "ExtractionValidator",
    "ExtractionCheckResult",
    "ExtractionIssue",
    "ExtractionSerializer",
    "ExtractionRegistry",
    "ExtractionReport",
    "ExtractionMetadata",
    "EXTRACTION_RESULT_VERSION",
    "ExtractionConfiguration",
    "ExtractionResult",
    "SourceType",
    "DocumentLoader",
    "DocumentContent",
    "DocumentParser",
    "ParsedDocument",
    "SectionDetector",
    "DetectedSection",
    "StrategyAnalyzer",
    "StrategyOverview",
    "IndicatorExtractor",
    "SmartMoneyExtractor",
    "EntryRuleExtractor",
    "ExitRuleExtractor",
    "RiskManagementExtractor",
    "SessionExtractor",
    "TimeframeExtractor",
    "ParameterExtractor",
    "MissingInformationDetector",
    "SDLGenerator",
    "IndicatorMention",
    "DetectorMention",
    "RuleMention",
    "RiskMention",
    "SessionMention",
    "TimeframeMention",
    "ParameterMention",
    "CategoryConfidence",
    "ConfidenceReport",
    "ExtractionWarning",
    "MissingInformationReport",
    "SDLValidationSummary",
    "ExtractionEngineError",
    "ExtractionConfigurationError",
    "ExtractionValidationError",
    "ExtractionExecutionError",
    "ExtractionNotFoundError",
    "ExtractionDisabledError",
    "ExtractionRegistrationError",
]
