"""The standardized input the AI Research Assistant consumes.

`AssistantContext` bundles exactly the sanctioned input sources for this
engine: a raw natural-language query, plus every already-built registry
this assistant is allowed to search. Every registry field is OPTIONAL --
a caller may attach as few or as many as it has available, and a query
answered with no registries attached simply returns an explicit "no
matching data found" answer, never a fabricated one. This engine never
rebuilds, mutates, or re-registers anything in any attached registry; it
only reads.
"""

from dataclasses import dataclass

from app.ai_assistant.models import AssistantConfiguration
from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.registry import KnowledgeRegistry
from app.portfolio_engine.registry import PortfolioRegistry
from app.research_engine.registry import ResearchRegistry
from app.sdl.registry import StrategyRegistry
from app.smart_money_engine.registry import SMCRegistry


@dataclass(frozen=True)
class AssistantContext:
    """Immutable wrapper around one query's inputs: the question, plus every readable source."""

    query: str
    configuration: AssistantConfiguration
    knowledge_registry: KnowledgeRegistry | None = None
    research_registry: ResearchRegistry | None = None
    portfolio_registry: PortfolioRegistry | None = None
    indicator_registry: IndicatorRegistry | None = None
    smc_registry: SMCRegistry | None = None
    strategy_registry: StrategyRegistry | None = None
