"""Compiles resolved strategy components into an immutable `StrategyModel`.

A pure transformation: given an SDL document and its already-validated
`ResolvedComponents`, build the dependency graph, the topologically
sorted execution pipeline, the context requirement, and a content
checksum. Never touches a registry itself -- that's `resolution.py`'s
job, run before validation and compilation.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.sdl.models import StrategyDefinition
from app.strategy_builder.exceptions import StrategyBuilderError
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION, StrategyMetadata
from app.strategy_builder.models import (
    ContextRequirement,
    DependencyEdge,
    DependencyGraph,
    ExecutionPipeline,
    ExecutionStep,
    StrategyModel,
)
from app.strategy_builder.resolution import ResolvedComponents
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyCompiler:
    """Builds a `StrategyModel` from an SDL document's resolved components."""

    def compile(self, sdl: StrategyDefinition, resolved: ResolvedComponents) -> StrategyModel:
        """Compile `resolved` (assumed already validated) into a `StrategyModel`.

        Raises:
            StrategyBuilderError: if a circular dependency slips through
                (defensive -- `StrategyValidator` should have caught it).
        """
        metadata = StrategyMetadata(
            id=sdl.metadata.id,
            name=sdl.metadata.name,
            description=sdl.metadata.description,
            category=sdl.metadata.category,
            sdl_version=sdl.metadata.sdl_version,
            strategy_version=sdl.metadata.strategy_version,
            model_version=STRATEGY_MODEL_VERSION,
        )

        context_requirement = ContextRequirement(
            symbols=tuple(sdl.symbols),
            timeframes=tuple(sdl.timeframes),
            primary_timeframe=sdl.primary_timeframe,
            sessions=tuple(sdl.sessions),
        )

        dependency_graph = self._build_dependency_graph(resolved)
        execution_pipeline = self._build_execution_pipeline(resolved)

        checksum = self._checksum(
            metadata=metadata,
            context_requirement=context_requirement,
            indicators=tuple(resolved.indicators),
            detectors=tuple(resolved.detectors),
            rules=tuple(resolved.rules),
            dependency_graph=dependency_graph,
            execution_pipeline=execution_pipeline,
        )

        model = StrategyModel(
            model_id=str(uuid.uuid4()),
            metadata=metadata,
            context_requirement=context_requirement,
            indicators=tuple(resolved.indicators),
            detectors=tuple(resolved.detectors),
            rules=tuple(resolved.rules),
            dependency_graph=dependency_graph,
            execution_pipeline=execution_pipeline,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Compiled strategy '%s' (checksum=%s, %d execution steps)",
            metadata.id,
            checksum[:12],
            len(execution_pipeline.steps),
        )
        return model

    @staticmethod
    def _build_dependency_graph(resolved: ResolvedComponents) -> DependencyGraph:
        nodes = tuple(resolved.all_component_names())
        edges = tuple(
            DependencyEdge(source=dependency, target=name)
            for name, deps in resolved.depends_on.items()
            for dependency in deps
        )
        return DependencyGraph(nodes=nodes, edges=edges)

    def _build_execution_pipeline(self, resolved: ResolvedComponents) -> ExecutionPipeline:
        kind_by_name: dict[str, str] = {}
        for ref in resolved.indicators:
            kind_by_name[ref.local_name] = "indicator"
        for ref in resolved.detectors:
            kind_by_name[ref.local_name] = "detector"
        for ref in resolved.rules:
            kind_by_name[ref.local_name] = "rule"

        order = self._topological_order(resolved.depends_on)
        steps = tuple(
            ExecutionStep(
                step_index=i,
                component_name=name,
                component_kind=kind_by_name.get(name, "rule"),
                depends_on=tuple(resolved.depends_on.get(name, [])),
            )
            for i, name in enumerate(order)
        )
        return ExecutionPipeline(steps=steps)

    @staticmethod
    def _topological_order(graph: dict[str, list[str]]) -> list[str]:
        order: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                raise StrategyBuilderError(f"Circular dependency detected while compiling: {node!r}")
            if node not in graph:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.discard(node)
            visited.add(node)
            order.append(node)

        for name in graph:
            visit(name)
        return order

    @staticmethod
    def _checksum(
        metadata: StrategyMetadata,
        context_requirement: ContextRequirement,
        indicators: tuple,
        detectors: tuple,
        rules: tuple,
        dependency_graph: DependencyGraph,
        execution_pipeline: ExecutionPipeline,
    ) -> str:
        """A content hash over everything except the identity/timestamp fields
        (`model_id`, `built_at`) -- two builds of the same SDL document produce
        the same checksum.
        """
        payload = {
            "metadata": metadata.model_dump(mode="json"),
            "context_requirement": context_requirement.model_dump(mode="json"),
            "indicators": [ref.model_dump(mode="json") for ref in indicators],
            "detectors": [ref.model_dump(mode="json") for ref in detectors],
            "rules": [ref.model_dump(mode="json") for ref in rules],
            "dependency_graph": dependency_graph.model_dump(mode="json"),
            "execution_pipeline": execution_pipeline.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
