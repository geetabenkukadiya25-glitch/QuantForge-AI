"""Top-level facade for the AI Strategy Extraction Engine.

`AIStrategyExtractionEngine` composes `ExtractionValidator` and
`ExtractionRunner` (which itself composes the full 15-stage pipeline)
into the single entrypoint most callers need. Converts external strategy
DOCUMENT TEXT (YouTube transcript, PDF, Markdown, plain text, Pine
Script, MQL4/MQL5, EasyLanguage, pseudocode, OCR text -- already
obtained by the caller; this engine never fetches, downloads, or OCRs
anything itself) into an `ExtractionResult`: a draft SDL document plus a
confidence report and a missing-information report. It MUST NOT
generate trading ideas -- it only extracts information already present
in the supplied text, and every output is an explicit DRAFT requiring
human review per `PROJECT_VISION.md`'s "AI assists, humans approve"
principle. Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.models import ExtractionConfiguration, ExtractionResult, SourceType
from app.ai_extraction.runner import ExtractionRunner, ExtractionSession
from app.core.base_engine import BaseEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.smart_money_engine.registry import SMCRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIStrategyExtractionEngine(BaseEngine):
    """Extracts a draft SDL strategy from already-obtained external document text.

    Consumes ONLY the supplied raw text plus, optionally, the Indicator
    Engine's and Smart Money Engine's registries -- solely to
    cross-reference mentions against real, currently registered names.
    It never computes an indicator, never detects a Smart Money
    structure, never connects to a broker or MT5, and never calls an
    external network service or AI API.
    """

    name = "AIStrategyExtractionEngine"

    def __init__(self, runner: ExtractionRunner | None = None) -> None:
        self._runner = runner or ExtractionRunner()

    def run(self, *args: Any, **kwargs: Any) -> ExtractionResult:
        """`BaseEngine`-style entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        raw_text: str,
        source_type: SourceType,
        configuration: ExtractionConfiguration | None = None,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
    ) -> ExtractionResult:
        """Run one extraction, raising on validation failure.

        Raises:
            ExtractionValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(self._build_context(raw_text, source_type, configuration, indicator_registry, smc_registry))

    def try_execute(
        self,
        raw_text: str,
        source_type: SourceType,
        configuration: ExtractionConfiguration | None = None,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
    ) -> ExtractionSession:
        """Run one extraction. Never raises -- inspect the returned session."""
        return self._runner.try_execute(self._build_context(raw_text, source_type, configuration, indicator_registry, smc_registry))

    @staticmethod
    def _build_context(raw_text, source_type, configuration, indicator_registry, smc_registry) -> ExtractionContext:
        return ExtractionContext(
            raw_text=raw_text,
            source_type=source_type,
            configuration=configuration or ExtractionConfiguration(),
            indicator_registry=indicator_registry,
            smc_registry=smc_registry,
        )
