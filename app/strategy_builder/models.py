"""The executable strategy model and its immutable, hashable building blocks.

Every model here is `frozen=True` -- hashable and immutable by
construction. Parameter dicts (which pydantic frozen models can't hash
directly) are stored as canonical JSON strings (`parameters_json`) rather
than raw `dict` fields, the same trade-off `app.sdl` and
`app.context_engine` make for their own frozen models.
"""

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.strategy_builder.metadata import StrategyMetadata


class StrategyBuilderModel(BaseModel):
    """Base class for every strategy_builder model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _dump_params(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, default=str)


class IndicatorReference(StrategyBuilderModel):
    """A resolved reference to an `app.indicator_engine` indicator."""

    local_name: str = Field(min_length=1, description="The strategy-local id (SDL IndicatorSpec.name).")
    type: str = Field(min_length=1, description="The registered indicator name (SDL IndicatorSpec.type).")
    parameters_json: str = "{}"
    timeframe: str | None = None

    @classmethod
    def create(cls, local_name: str, type_: str, params: dict[str, Any], timeframe: str | None = None) -> "IndicatorReference":
        return cls(local_name=local_name, type=type_, parameters_json=_dump_params(params), timeframe=timeframe)


class DetectorReference(StrategyBuilderModel):
    """A resolved reference to an `app.smart_money_engine` detector."""

    local_name: str = Field(min_length=1, description="The strategy-local id (SDL IndicatorSpec.name).")
    type: str = Field(min_length=1, description="The registered detector name (SDL IndicatorSpec.type).")
    parameters_json: str = "{}"
    timeframe: str | None = None

    @classmethod
    def create(cls, local_name: str, type_: str, params: dict[str, Any], timeframe: str | None = None) -> "DetectorReference":
        return cls(local_name=local_name, type=type_, parameters_json=_dump_params(params), timeframe=timeframe)


class RuleReference(StrategyBuilderModel):
    """A named SDL rule (filter/entry/exit) participating in the execution pipeline.

    The rule's `condition` text is carried through untouched -- the
    Strategy Builder never interprets or evaluates it.
    """

    local_name: str = Field(min_length=1)
    section: str = Field(min_length=1, description='"filters" | "entry_rules" | "exit_rules".')
    condition: str = Field(min_length=1)


class ContextRequirement(StrategyBuilderModel):
    """The Market Context the strategy needs -- a requirement, not a live snapshot."""

    symbols: tuple[str, ...] = Field(min_length=1)
    timeframes: tuple[str, ...] = Field(min_length=1)
    primary_timeframe: str | None = None
    sessions: tuple[str, ...] = Field(default_factory=tuple)


class DependencyEdge(StrategyBuilderModel):
    """A directed edge: `target` depends on `source`."""

    source: str
    target: str


class DependencyGraph(StrategyBuilderModel):
    """The full dependency graph over every named component in the strategy."""

    nodes: tuple[str, ...]
    edges: tuple[DependencyEdge, ...] = Field(default_factory=tuple)


class ExecutionStep(StrategyBuilderModel):
    """One step in the resolved execution pipeline."""

    step_index: int = Field(ge=0)
    component_name: str
    component_kind: str = Field(description='"indicator" | "detector" | "rule".')
    depends_on: tuple[str, ...] = Field(default_factory=tuple)


class ExecutionPipeline(StrategyBuilderModel):
    """The full, dependency-ordered execution pipeline description."""

    steps: tuple[ExecutionStep, ...]

    def describe(self) -> str:
        """A human-readable, numbered description of the pipeline."""
        lines = []
        for step in self.steps:
            deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
            lines.append(f"{step.step_index + 1}. [{step.component_kind}] {step.component_name}{deps}")
        return "\n".join(lines)


class StrategyModel(StrategyBuilderModel):
    """The complete, executable strategy model.

    Immutable, serializable, versioned, and hashable -- the single
    artifact future engines (Backtesting Engine, Optimization Engine,
    Replay Engine) will consume instead of re-resolving SDL documents
    themselves.
    """

    model_id: str = Field(min_length=1, description="Unique id for this specific build.")
    metadata: StrategyMetadata
    context_requirement: ContextRequirement
    indicators: tuple[IndicatorReference, ...] = Field(default_factory=tuple)
    detectors: tuple[DetectorReference, ...] = Field(default_factory=tuple)
    rules: tuple[RuleReference, ...] = Field(default_factory=tuple)
    dependency_graph: DependencyGraph
    execution_pipeline: ExecutionPipeline
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
