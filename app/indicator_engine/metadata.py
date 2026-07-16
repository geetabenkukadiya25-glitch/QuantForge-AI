"""Static, self-describing contract every indicator exposes.

Every `BaseIndicator` subclass returns an `IndicatorMetadata` describing
its name, category, required input columns, output series names,
parameter specification, and version -- used by `IndicatorRegistry`,
`IndicatorValidator`, and the Streamlit Indicator Explorer, so none of
them hardcode per-indicator knowledge.
"""

from dataclasses import dataclass, field
from typing import Any

INDICATOR_METADATA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ParameterSpec:
    """Describes one tunable parameter an indicator accepts."""

    name: str
    type: str  # "int" | "float" | "str" | "bool"
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    description: str = ""


@dataclass(frozen=True)
class IndicatorMetadata:
    """The complete, static description of an indicator."""

    name: str
    category: str
    description: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)
    version: str = "1.0.0"

    def default_params(self) -> dict[str, Any]:
        """Return `{param_name: default_value}` for every declared parameter."""
        return {spec.name: spec.default for spec in self.parameters}

    def parameter_spec(self, name: str) -> ParameterSpec:
        """Look up a single parameter's spec by name.

        Raises:
            KeyError: if `name` isn't a declared parameter.
        """
        for spec in self.parameters:
            if spec.name == name:
                return spec
        raise KeyError(f"Indicator {self.name!r} has no parameter {name!r}")
