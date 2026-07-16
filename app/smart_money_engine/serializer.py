"""Serializes `SMCResult`s and `SMCMetadata` to dict/JSON/YAML."""

import json
from dataclasses import asdict
from typing import Any

import yaml

from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCResult


class SMCSerializer:
    """Converts `SMCResult`/`SMCMetadata` to plain dict/JSON/YAML."""

    def to_dict(self, result: SMCResult) -> dict[str, Any]:
        """Return `result` as a plain, JSON-safe dict."""
        return result.to_dict()

    def to_json(self, result: SMCResult, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(result)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, result: SMCResult, canonical: bool = False) -> str:
        data = self.to_dict(result)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)

    def metadata_to_dict(self, metadata: SMCMetadata) -> dict[str, Any]:
        """Return `metadata` as a plain, JSON-safe dict (for docs/UI display)."""
        return asdict(metadata)

    def metadata_to_json(self, metadata: SMCMetadata, pretty: bool = True) -> str:
        return json.dumps(self.metadata_to_dict(metadata), indent=2 if pretty else None)
