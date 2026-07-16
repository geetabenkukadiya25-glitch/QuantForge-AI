"""Static, self-describing contract every detector exposes.

Every `BaseSMCDetector` subclass returns an `SMCMetadata` describing its
name, category, required input columns, output kinds, parameter
specification, and version -- used by `SMCRegistry`, `SMCValidator`, and
the Streamlit Smart Money Explorer, so none of them hardcode
per-detector knowledge.
"""

from dataclasses import dataclass, field
from typing import Any

SMC_METADATA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ParameterSpec:
    """Describes one tunable parameter a detector accepts."""

    name: str
    type: str  # "int" | "float" | "str" | "bool"
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    description: str = ""


@dataclass(frozen=True)
class SMCMetadata:
    """The complete, static description of a Smart Money detector."""

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
        raise KeyError(f"Detector {self.name!r} has no parameter {name!r}")
