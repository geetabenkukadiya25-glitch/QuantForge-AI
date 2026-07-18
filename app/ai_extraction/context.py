"""The standardized input the AI Strategy Extraction Engine consumes.

`ExtractionContext` bundles exactly the sanctioned input for this
module: raw document text plus its declared `SourceType` (REQUIRED --
this engine never fetches a YouTube video, downloads a PDF, or performs
OCR itself; it only processes text a caller has already obtained from
one of those sources, per `PROJECT_VISION.md`'s "No External APIs"
convention). `indicator_registry`/`smc_registry` are OPTIONAL and
consumed ONLY to cross-reference mentions against real, currently
registered names -- the same "single source of truth" discipline every
other engine in this platform uses.
"""

from dataclasses import dataclass

from app.ai_extraction.models import ExtractionConfiguration, SourceType
from app.indicator_engine.registry import IndicatorRegistry
from app.smart_money_engine.registry import SMCRegistry


@dataclass(frozen=True)
class ExtractionContext:
    """Immutable wrapper around one extraction run's inputs."""

    raw_text: str
    source_type: SourceType
    configuration: ExtractionConfiguration
    indicator_registry: IndicatorRegistry | None = None
    smc_registry: SMCRegistry | None = None
