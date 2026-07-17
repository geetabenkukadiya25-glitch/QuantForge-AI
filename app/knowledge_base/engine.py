"""Top-level facade for the Knowledge Base Platform.

`KnowledgeBaseEngine` composes `KnowledgeValidator`, `KnowledgeCompiler`,
and `KnowledgeRunner` into the single entrypoint most callers need. This
is an institutional documentation and trading-knowledge system -- NOT
AI, NOT Strategy Builder, NOT the Research Engine. It stores, indexes,
and serves authored `KnowledgeEntry` content; it NEVER executes a trade,
NEVER optimizes, NEVER backtests, NEVER validates, NEVER replays, and
NEVER connects to a broker or MT5. Implements `BaseEngine` (`run`
aliases `execute`).
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.models import KnowledgeConfiguration, KnowledgeEntry, KnowledgeResult
from app.knowledge_base.runner import KnowledgeRunner, KnowledgeSession
from app.smart_money_engine.registry import SMCRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseEngine(BaseEngine):
    """Builds and serves an institutional trading-knowledge base.

    Consumes ONLY authored `KnowledgeEntry` content plus, optionally, the
    Indicator Engine's and Smart Money Engine's registries -- solely to
    validate that documentation cross-references real, currently
    registered names. It never computes an indicator, never detects a
    Smart Money structure, and never re-invokes any other engine's logic.
    """

    name = "KnowledgeBaseEngine"

    def __init__(self, runner: KnowledgeRunner | None = None) -> None:
        self._runner = runner or KnowledgeRunner()

    def run(self, *args: Any, **kwargs: Any) -> KnowledgeResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        entries: tuple[KnowledgeEntry, ...],
        configuration: KnowledgeConfiguration,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
    ) -> KnowledgeResult:
        """Build one knowledge base, raising on validation failure.

        Raises:
            KnowledgeValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(KnowledgeContext(entries=entries, configuration=configuration, indicator_registry=indicator_registry, smc_registry=smc_registry))

    def try_execute(
        self,
        entries: tuple[KnowledgeEntry, ...],
        configuration: KnowledgeConfiguration,
        indicator_registry: IndicatorRegistry | None = None,
        smc_registry: SMCRegistry | None = None,
    ) -> KnowledgeSession:
        """Build one knowledge base. Never raises -- inspect the returned session."""
        return self._runner.try_execute(KnowledgeContext(entries=entries, configuration=configuration, indicator_registry=indicator_registry, smc_registry=smc_registry))
