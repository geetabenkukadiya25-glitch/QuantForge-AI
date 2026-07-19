"""Serializes `CloudBuild`s to dict/JSON/YAML."""

import json

import yaml

from app.cloud_platform.models import CloudBuild


class CloudSerializer:
    """Converts `CloudBuild` instances to plain dict/JSON/YAML."""

    def to_dict(self, build: CloudBuild) -> dict:
        """Return `build` as a plain, JSON-safe dict."""
        return build.model_dump(mode="json")

    def to_json(self, build: CloudBuild, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(build)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, build: CloudBuild, canonical: bool = False) -> str:
        data = self.to_dict(build)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)
