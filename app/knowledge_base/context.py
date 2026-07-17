"""The standardized input the Knowledge Base Platform consumes.

`KnowledgeContext` bundles exactly the sanctioned input for this module:
a tuple of authored `KnowledgeEntry` records plus a `KnowledgeConfiguration`.
`indicator_registry`/`smc_registry` are OPTIONAL and consumed ONLY to
validate that an entry's `related_indicator_types`/`related_detector_types`
cross-references point at real, currently-registered names -- the same
"single source of truth" discipline that caught the outdated
`SESSION_RANGE_HIGH`/`SESSION_RANGE_LOW` SDL example. This module never
computes an indicator, never detects a Smart Money structure, and never
executes a trade -- it only documents them.
"""

from dataclasses import dataclass

from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.models import KnowledgeConfiguration, KnowledgeEntry
from app.smart_money_engine.registry import SMCRegistry


@dataclass(frozen=True)
class KnowledgeContext:
    """Immutable wrapper around one knowledge base build's inputs."""

    entries: tuple[KnowledgeEntry, ...]
    configuration: KnowledgeConfiguration
    indicator_registry: IndicatorRegistry | None = None
    smc_registry: SMCRegistry | None = None
