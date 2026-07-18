"""Serializes `StrategyDefinition` documents to dict/JSON/YAML.

"Canonical" output means deterministically ordered keys and stable
formatting -- useful for diffing two strategy revisions or hashing a
document (see `StrategyCompiler`'s checksum).
"""

import json

import yaml

from app.core.checksums import canonical_json
from app.sdl.models import StrategyDefinition


class StrategySerializer:
    """Converts `StrategyDefinition` instances to/from plain dict/JSON/YAML."""

    def to_dict(self, definition: StrategyDefinition) -> dict:
        """Return `definition` as a plain dict (JSON-safe: no datetimes, no enums)."""
        return definition.model_dump(mode="json", exclude_none=False)

    def from_dict(self, data: dict) -> StrategyDefinition:
        """Build a `StrategyDefinition` from a plain dict (structural validation only).

        Raises:
            pydantic.ValidationError: if `data` fails schema validation. Prefer
                `StrategyValidator.validate` for a non-raising, reportable outcome.
        """
        return StrategyDefinition.model_validate(data)

    def to_json(self, definition: StrategyDefinition, pretty: bool = True, canonical: bool = False) -> str:
        """Serialize `definition` to a JSON string."""
        data = self.to_dict(definition)
        if canonical:
            return canonical_json(data)
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, definition: StrategyDefinition, canonical: bool = False) -> str:
        """Serialize `definition` to a YAML string."""
        data = self.to_dict(definition)
        return yaml.safe_dump(
            data,
            sort_keys=canonical,
            default_flow_style=False,
            allow_unicode=True,
        )
