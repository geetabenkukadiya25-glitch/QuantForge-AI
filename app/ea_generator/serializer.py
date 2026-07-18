"""Serializes `EAGeneratorResult`s to dict/JSON/YAML/MQL5 source."""

import json

import yaml

from app.ea_generator.models import EAGeneratorResult


class EAGeneratorSerializer:
    """Converts `EAGeneratorResult` instances to plain dict/JSON/YAML, or the raw `.mq5` source."""

    def to_dict(self, result: EAGeneratorResult) -> dict:
        """Return `result` as a plain, JSON-safe dict."""
        return result.model_dump(mode="json")

    def to_json(self, result: EAGeneratorResult, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(result)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, result: EAGeneratorResult, canonical: bool = False) -> str:
        data = self.to_dict(result)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)

    def to_mq5(self, result: EAGeneratorResult) -> str:
        """Return the generated `.mq5` source text, unchanged."""
        return result.source_code
