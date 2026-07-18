"""Top-level facade for the AI Research Assistant.

`AIResearchAssistantEngine` composes `AssistantValidator`,
`AssistantCompiler`, and `AssistantRunner` into the single entrypoint
most callers need. It is a deterministic, offline assistant -- NOT an
LLM, and it NEVER calls any external AI API or service. It only
searches and explains data already present inside
QuantForge AI's own registries and documentation. It is strictly
read-only: it NEVER executes a trade, NEVER optimizes, NEVER validates,
NEVER replays, NEVER rebuilds a strategy, and NEVER connects to a broker
or MT5. Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import AssistantConfiguration, AssistantResult
from app.ai_assistant.runner import AssistantRunner, AssistantSession
from app.core.base_engine import BaseEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.registry import KnowledgeRegistry
from app.portfolio_engine.registry import PortfolioRegistry
from app.research_engine.registry import ResearchRegistry
from app.sdl.registry import StrategyRegistry
from app.smart_money_engine.registry import SMCRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIResearchAssistantEngine(BaseEngine):
    """Answers natural-language questions using ONLY QuantForge AI's own registered data.

    Every attached registry is optional; a query with nothing attached
    still answers deterministically, either from the static engine
    glossary (`knowledge.py`) or with an explicit "no matching data
    found" section -- never a fabricated answer.
    """

    name = "AIResearchAssistantEngine"

    def __init__(self, runner: AssistantRunner | None = None) -> None:
        self._runner = runner or AssistantRunner()

    def run(self, *args: Any, **kwargs: Any) -> AssistantResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        query: str,
        configuration: AssistantConfiguration | None = None,
        knowledge_registry: KnowledgeRegistry | None = None,
        research_registry: ResearchRegistry | None = None,
        portfolio_registry: PortfolioRegistry | None = None,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
        strategy_registry: StrategyRegistry | None = None,
    ) -> AssistantResult:
        """Answer one query, raising on validation failure.

        Raises:
            AssistantValidationError: if the context fails pre-execution validation.
        """
        context = self._build_context(query, configuration, knowledge_registry, research_registry, portfolio_registry, indicator_registry, smc_registry, strategy_registry)
        return self._runner.execute(context)

    def try_execute(
        self,
        query: str,
        configuration: AssistantConfiguration | None = None,
        knowledge_registry: KnowledgeRegistry | None = None,
        research_registry: ResearchRegistry | None = None,
        portfolio_registry: PortfolioRegistry | None = None,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
        strategy_registry: StrategyRegistry | None = None,
    ) -> AssistantSession:
        """Answer one query. Never raises -- inspect the returned session."""
        context = self._build_context(query, configuration, knowledge_registry, research_registry, portfolio_registry, indicator_registry, smc_registry, strategy_registry)
        return self._runner.try_execute(context)

    @staticmethod
    def _build_context(
        query: str,
        configuration: AssistantConfiguration | None,
        knowledge_registry: KnowledgeRegistry | None,
        research_registry: ResearchRegistry | None,
        portfolio_registry: PortfolioRegistry | None,
        indicator_registry: IndicatorRegistry | None,
        smc_registry: SMCRegistry | None,
        strategy_registry: StrategyRegistry | None,
    ) -> AssistantContext:
        return AssistantContext(
            query=query,
            configuration=configuration or AssistantConfiguration(),
            knowledge_registry=knowledge_registry,
            research_registry=research_registry,
            portfolio_registry=portfolio_registry,
            indicator_registry=indicator_registry,
            smc_registry=smc_registry,
            strategy_registry=strategy_registry,
        )
