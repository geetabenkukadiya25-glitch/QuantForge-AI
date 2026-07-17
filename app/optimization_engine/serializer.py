"""Serializes `OptimizationResult`s to dict/JSON/YAML."""

import json

import yaml

from app.optimization_engine.models import OptimizationResult


class OptimizationSerializer:
    """Converts `OptimizationResult` instances to plain dict/JSON/YAML."""

    def to_dict(self, result: OptimizationResult) -> dict:
        """Return `result` as a plain, JSON-safe dict."""
        return result.model_dump(mode="json")

    def to_json(self, result: OptimizationResult, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(result)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, result: OptimizationResult, canonical: bool = False) -> str:
        data = self.to_dict(result)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)
