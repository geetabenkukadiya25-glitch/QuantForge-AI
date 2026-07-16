"""Compiles a validated strategy document into an internal execution model.

`StrategyCompiler` does NOT generate Python or MQL5 -- it produces a
`CompiledStrategy`: the validated, normalized `StrategyDefinition` plus a
dependency-resolved execution order and a content checksum. Every future
engine (Indicator Engine, Backtesting Engine, EA Generator, ...) consumes
this same compiled form instead of re-parsing/re-validating raw
documents, keeping strategy interpretation consistent platform-wide.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.base_engine import BaseEngine
from app.sdl.exceptions import SDLCompileError, SDLValidationError
from app.sdl.models import StrategyDefinition
from app.sdl.serializer import StrategySerializer
from app.sdl.validator import StrategyValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CompiledStrategy:
    """A validated, normalized strategy ready for downstream engines."""

    definition: StrategyDefinition
    execution_order: list[str]
    checksum: str
    sdl_version: str
    compiled_at: datetime


class StrategyCompiler(BaseEngine):
    """Validates and normalizes a strategy document into a `CompiledStrategy`.

    Implements `BaseEngine` (the platform's engine-based architecture
    contract, per `PROJECT_VISION.md`) -- `run()` is an alias for
    `compile()`.
    """

    name = "StrategyCompiler"

    def __init__(
        self,
        validator: StrategyValidator | None = None,
        serializer: StrategySerializer | None = None,
    ) -> None:
        self._validator = validator or StrategyValidator()
        self._serializer = serializer or StrategySerializer()

    def run(self, *args: Any, **kwargs: Any) -> CompiledStrategy:
        """`BaseEngine` entrypoint; delegates to `compile`."""
        return self.compile(*args, **kwargs)

    def compile(self, document: StrategyDefinition | dict) -> CompiledStrategy:
        """Validate and compile `document` into a `CompiledStrategy`.

        Raises:
            SDLValidationError: if `document` fails validation.
        """
        result = self._validator.validate(document)
        if not result.is_valid:
            raise SDLValidationError(result.errors)

        definition = result.definition
        assert definition is not None  # guaranteed by is_valid

        execution_order = self._resolve_execution_order(definition)
        checksum = self._checksum(definition)

        compiled = CompiledStrategy(
            definition=definition,
            execution_order=execution_order,
            checksum=checksum,
            sdl_version=definition.metadata.sdl_version,
            compiled_at=datetime.now(timezone.utc),
        )
        logger.info(
            "Compiled strategy '%s' (checksum=%s, %d execution steps)",
            definition.metadata.id,
            checksum[:12],
            len(execution_order),
        )
        return compiled

    def _resolve_execution_order(self, definition: StrategyDefinition) -> list[str]:
        """Topologically sort indicators/filters/entry/exit rules by `depends_on`."""
        graph: dict[str, list[str]] = {}
        for section in ("indicators", "filters", "entry_rules", "exit_rules"):
            for item in getattr(definition, section):
                graph[item.name] = list(item.depends_on)

        order: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                raise SDLCompileError(f"Circular dependency detected while compiling: {node!r}")
            if node not in graph:
                return  # dependency on an item outside the resolvable sections
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.discard(node)
            visited.add(node)
            order.append(node)

        for name in graph:
            visit(name)
        return order

    def _checksum(self, definition: StrategyDefinition) -> str:
        canonical = self._serializer.to_json(definition, canonical=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
