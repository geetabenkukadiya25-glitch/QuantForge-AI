"""Serializes `StrategyModel`s to dict/JSON/YAML."""

import json

import yaml

from app.strategy_builder.models import StrategyModel


class StrategySerializer:
    """Converts `StrategyModel` instances to plain dict/JSON/YAML."""

    def to_dict(self, model: StrategyModel) -> dict:
        """Return `model` as a plain, JSON-safe dict."""
        return model.model_dump(mode="json")

    def to_json(self, model: StrategyModel, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(model)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, model: StrategyModel, canonical: bool = False) -> str:
        data = self.to_dict(model)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)
