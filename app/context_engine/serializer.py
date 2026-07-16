"""Serializes `ContextSnapshot`s to dict/JSON/YAML."""

import json

import yaml

from app.context_engine.models import ContextSnapshot


class ContextSerializer:
    """Converts `ContextSnapshot` instances to/from plain dict/JSON/YAML."""

    def to_dict(self, snapshot: ContextSnapshot) -> dict:
        """Return `snapshot` as a plain, JSON-safe dict."""
        return snapshot.model_dump(mode="json")

    def from_dict(self, data: dict) -> ContextSnapshot:
        """Build a `ContextSnapshot` from a plain dict (raises on schema mismatch)."""
        return ContextSnapshot.model_validate(data)

    def to_json(self, snapshot: ContextSnapshot, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(snapshot)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, snapshot: ContextSnapshot, canonical: bool = False) -> str:
        data = self.to_dict(snapshot)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)
