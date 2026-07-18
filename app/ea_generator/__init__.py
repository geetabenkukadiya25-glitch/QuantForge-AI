"""Professional EA Generator Engine.

This is the official Phase 16 of `PROJECT_VISION.md`'s Approved
Roadmap ("EA Generator"). An OFFLINE CODE GENERATOR ONLY: it generates
production-quality-skeleton MetaTrader 5 (MQL5) Expert Advisor source
code from an already-built, already-validated `StrategyModel`. It does
NOT compile MT5, does NOT execute trades, does NOT connect to a broker,
does NOT call MetaTrader, does NOT run a Python bridge, and does NOT
call any external API -- it only reads already-completed engine outputs
and emits text.

Consumes ONLY a `StrategyModel` (REQUIRED, from `app.strategy_builder`),
plus optionally already-completed `ValidationResult`/`OptimizationResult`/
`ResearchResult`/`PortfolioResult` outputs -- it never rebuilds any of
them, never duplicates SDL, never duplicates `StrategyModel`, and never
duplicates any registry. Deterministic by construction: the same input
always produces identical generated source and an identical checksum,
using the shared `app.core.checksums` helper every other engine's
compiler already uses.
"""

from app.ea_generator.compiler import EACompiler
from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.engine import EAGeneratorEngine
from app.ea_generator.exceptions import (
    EAConfigurationError,
    EADisabledError,
    EAExecutionError,
    EAGeneratorEngineError,
    EANotFoundError,
    EARegistrationError,
    EAValidationError,
)
from app.ea_generator.generator import EAGenerator, GenerationArtifacts
from app.ea_generator.indicators import IndicatorCodeGenerator
from app.ea_generator.metadata import EA_RESULT_VERSION, EAGeneratorMetadata
from app.ea_generator.models import (
    EAGeneratorConfiguration,
    EAGeneratorResult,
    EAGeneratorStatistics,
    GeneratedIndicatorDeclaration,
    GeneratedInput,
    GeneratedRiskParameters,
    GeneratedRuleBlock,
    GeneratedTradeManagement,
)
from app.ea_generator.parameters import ParameterCodeGenerator
from app.ea_generator.registry import EAGeneratorRegistry
from app.ea_generator.report import EAGeneratorReport
from app.ea_generator.risk import RiskCodeGenerator
from app.ea_generator.runner import BaseEAGeneratorRunner, EAGeneratorRunner, EAGeneratorSession, SessionStatus
from app.ea_generator.serializer import EAGeneratorSerializer
from app.ea_generator.statistics import EAGeneratorStatisticsEngine
from app.ea_generator.trade_management import TradeManagementCodeGenerator
from app.ea_generator.validator import EAGeneratorCheckResult, EAGeneratorIssue, EAGeneratorValidator

__all__ = [
    "EAGeneratorEngine",
    "EAGeneratorRunner",
    "BaseEAGeneratorRunner",
    "EAGeneratorSession",
    "SessionStatus",
    "EAGeneratorContext",
    "EACompiler",
    "EAGeneratorValidator",
    "EAGeneratorCheckResult",
    "EAGeneratorIssue",
    "EAGeneratorSerializer",
    "EAGeneratorRegistry",
    "EAGeneratorReport",
    "EAGeneratorMetadata",
    "EA_RESULT_VERSION",
    "EAGeneratorConfiguration",
    "EAGeneratorResult",
    "EAGeneratorStatistics",
    "GeneratedInput",
    "GeneratedIndicatorDeclaration",
    "GeneratedRiskParameters",
    "GeneratedRuleBlock",
    "GeneratedTradeManagement",
    "EAGenerator",
    "GenerationArtifacts",
    "IndicatorCodeGenerator",
    "ParameterCodeGenerator",
    "RiskCodeGenerator",
    "TradeManagementCodeGenerator",
    "EAGeneratorStatisticsEngine",
    "EAGeneratorEngineError",
    "EAConfigurationError",
    "EAValidationError",
    "EAExecutionError",
    "EANotFoundError",
    "EADisabledError",
    "EARegistrationError",
]
