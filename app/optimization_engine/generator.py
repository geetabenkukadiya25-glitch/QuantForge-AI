"""Turns `ParameterDefinition`s into concrete values, and values into new artifacts.

`ParameterGenerator` is a pure-function toolkit with two jobs:

1. Enumerate (`values_for`) or sample (`sample`) the concrete values one
   `ParameterDefinition` can take -- shared by `GridSearchOptimizer` and
   `RandomSearchOptimizer` so both search methods agree on what a
   dimension's legal values are.
2. Apply a candidate's `{name: value}` assignment onto the BASE
   `StrategyModel`/`BacktestConfiguration`, producing NEW, independent
   copies (`apply_to_model`/`apply_to_configuration`). This is how "Create
   StrategyModel" happens per candidate without ever re-invoking
   `app.strategy_builder` -- `StrategyModel`'s own fields are frozen
   Pydantic models, so `model_copy(update=...)` is enough. The checksum
   for a derived model is recomputed here, using the exact same
   content-hash shape `StrategyCompiler._checksum` uses (metadata,
   context_requirement, indicators, detectors, rules, dependency_graph,
   execution_pipeline) -- an intentionally duplicated small utility, not
   a modification to Strategy Builder's own code.
"""

import json
import random
import uuid
from typing import Any

from app.backtesting_engine.models import BacktestConfiguration
from app.core.checksums import compute_checksum
from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.models import ParameterDefinition, ParameterKind, ParameterTarget
from app.strategy_builder.models import DetectorReference, IndicatorReference, StrategyModel

_FLOAT_ROUNDING = 10


class ParameterGenerator:
    """Pure functions: enumerate/sample parameter values, and apply them to artifacts."""

    @staticmethod
    def values_for(definition: ParameterDefinition) -> tuple[Any, ...]:
        """The full, discrete set of legal values for `definition` -- used by grid search."""
        if definition.kind == ParameterKind.BOOLEAN:
            return (True, False)
        if definition.kind == ParameterKind.ENUM:
            return tuple(json.loads(definition.choices_json))
        if definition.kind == ParameterKind.FIXED:
            if definition.fixed_value_json is None:
                raise OptimizationConfigurationError(f"Parameter {definition.name!r} is FIXED but has no fixed_value_json.")
            return (json.loads(definition.fixed_value_json),)
        if definition.kind == ParameterKind.INTEGER:
            step = int(definition.step) if definition.step else 1
            lo, hi = int(definition.min_value), int(definition.max_value)
            return tuple(range(lo, hi + 1, step))
        if definition.kind == ParameterKind.FLOAT:
            step = definition.step if definition.step else 1.0
            lo, hi = definition.min_value, definition.max_value
            values = []
            value = lo
            while value <= hi + 1e-9:
                values.append(round(value, _FLOAT_ROUNDING))
                value += step
            return tuple(values)
        raise OptimizationConfigurationError(f"Unknown parameter kind: {definition.kind!r}")

    @staticmethod
    def sample(definition: ParameterDefinition, rng: random.Random) -> Any:
        """One randomly sampled legal value for `definition` -- used by random search."""
        if definition.kind == ParameterKind.BOOLEAN:
            return rng.choice([True, False])
        if definition.kind == ParameterKind.ENUM:
            return rng.choice(json.loads(definition.choices_json))
        if definition.kind == ParameterKind.FIXED:
            if definition.fixed_value_json is None:
                raise OptimizationConfigurationError(f"Parameter {definition.name!r} is FIXED but has no fixed_value_json.")
            return json.loads(definition.fixed_value_json)
        if definition.kind == ParameterKind.INTEGER:
            step = int(definition.step) if definition.step else 1
            lo, hi = int(definition.min_value), int(definition.max_value)
            return rng.randrange(lo, hi + 1, step)
        if definition.kind == ParameterKind.FLOAT:
            return round(rng.uniform(definition.min_value, definition.max_value), _FLOAT_ROUNDING)
        raise OptimizationConfigurationError(f"Unknown parameter kind: {definition.kind!r}")

    @staticmethod
    def parse_target(name: str) -> tuple[ParameterTarget, str, str | None]:
        """Parse a dotted target path into `(target, local_name_or_field, param_name)`."""
        parts = name.split(".")
        if len(parts) == 3 and parts[0] == "component":
            return ParameterTarget.COMPONENT, parts[1], parts[2]
        if len(parts) == 2 and parts[0] == "configuration":
            return ParameterTarget.CONFIGURATION, parts[1], None
        raise OptimizationConfigurationError(
            f"Invalid parameter target {name!r}: expected 'component.<local_name>.<param>' or 'configuration.<field>'."
        )

    @classmethod
    def apply_to_model(cls, base_model: StrategyModel, values: dict[str, Any]) -> StrategyModel:
        """Return a NEW `StrategyModel` with `values` applied to matching component references."""
        indicator_overrides: dict[str, dict[str, Any]] = {}
        detector_overrides: dict[str, dict[str, Any]] = {}

        for name, value in values.items():
            target, local_name, param_name = cls.parse_target(name)
            if target != ParameterTarget.COMPONENT:
                continue
            if any(ref.local_name == local_name for ref in base_model.indicators):
                indicator_overrides.setdefault(local_name, {})[param_name] = value
            elif any(ref.local_name == local_name for ref in base_model.detectors):
                detector_overrides.setdefault(local_name, {})[param_name] = value
            else:
                raise OptimizationConfigurationError(f"Unknown component {local_name!r} referenced by parameter {name!r}.")

        new_indicators = tuple(cls._apply_reference_overrides(ref, indicator_overrides.get(ref.local_name)) for ref in base_model.indicators)
        new_detectors = tuple(cls._apply_reference_overrides(ref, detector_overrides.get(ref.local_name)) for ref in base_model.detectors)

        checksum = cls.recompute_checksum(
            metadata=base_model.metadata,
            context_requirement=base_model.context_requirement,
            indicators=new_indicators,
            detectors=new_detectors,
            rules=base_model.rules,
            dependency_graph=base_model.dependency_graph,
            execution_pipeline=base_model.execution_pipeline,
        )
        # Deterministic, content-derived model_id (not uuid4): two optimization
        # runs over the same base model + candidate values must produce the
        # same derived StrategyModel.model_id, or every downstream checksum
        # (BacktestResult, OptimizationResult) would be non-deterministic too.
        model_id = str(uuid.uuid5(uuid.NAMESPACE_OID, checksum))
        return base_model.model_copy(
            update={
                "model_id": model_id,
                "indicators": new_indicators,
                "detectors": new_detectors,
                "checksum": checksum,
            }
        )

    @staticmethod
    def _apply_reference_overrides(ref: IndicatorReference | DetectorReference, overrides: dict[str, Any] | None):
        if not overrides:
            return ref
        params = json.loads(ref.parameters_json)
        params.update(overrides)
        new_json = json.dumps(params, sort_keys=True, default=str)
        return ref.model_copy(update={"parameters_json": new_json})

    @classmethod
    def apply_to_configuration(cls, base_configuration: BacktestConfiguration, values: dict[str, Any]) -> BacktestConfiguration:
        """Return a NEW `BacktestConfiguration` with `values` applied to matching fields."""
        overrides: dict[str, Any] = {}
        for name, value in values.items():
            target, field_name, _ = cls.parse_target(name)
            if target != ParameterTarget.CONFIGURATION:
                continue
            if field_name not in BacktestConfiguration.model_fields:
                raise OptimizationConfigurationError(f"Unknown BacktestConfiguration field {field_name!r} referenced by parameter {name!r}.")
            overrides[field_name] = value
        if not overrides:
            return base_configuration
        # `model_copy(update=...)` skips field validation entirely -- rebuild
        # via the constructor instead so out-of-range candidate values (e.g.
        # a negative take_profit_points) are rejected here, per-candidate,
        # rather than silently accepted.
        return BacktestConfiguration(**{**base_configuration.model_dump(), **overrides})

    @staticmethod
    def recompute_checksum(metadata, context_requirement, indicators, detectors, rules, dependency_graph, execution_pipeline) -> str:
        """The same content-hash shape `StrategyCompiler._checksum` uses (metadata excluded of nothing extra)."""
        payload = {
            "metadata": metadata.model_dump(mode="json"),
            "context_requirement": context_requirement.model_dump(mode="json"),
            "indicators": [ref.model_dump(mode="json") for ref in indicators],
            "detectors": [ref.model_dump(mode="json") for ref in detectors],
            "rules": [ref.model_dump(mode="json") for ref in rules],
            "dependency_graph": dependency_graph.model_dump(mode="json"),
            "execution_pipeline": execution_pipeline.model_dump(mode="json"),
        }
        return compute_checksum(payload)
