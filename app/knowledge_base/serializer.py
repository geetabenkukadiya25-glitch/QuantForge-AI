"""Serializes `KnowledgeResult`s (and individual `KnowledgeEntry`s) to dict/JSON/YAML."""

import json

import yaml

from app.knowledge_base.models import KnowledgeEntry, KnowledgeResult


class KnowledgeSerializer:
    """Converts `KnowledgeResult`/`KnowledgeEntry` instances to plain dict/JSON/YAML."""

    def to_dict(self, result: KnowledgeResult) -> dict:
        """Return `result` as a plain, JSON-safe dict."""
        return result.model_dump(mode="json")

    def to_json(self, result: KnowledgeResult, pretty: bool = True, canonical: bool = False) -> str:
        data = self.to_dict(result)
        if canonical:
            return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, indent=2 if pretty else None, sort_keys=False)

    def to_yaml(self, result: KnowledgeResult, canonical: bool = False) -> str:
        data = self.to_dict(result)
        return yaml.safe_dump(data, sort_keys=canonical, default_flow_style=False, allow_unicode=True)

    def entry_to_dict(self, entry: KnowledgeEntry) -> dict:
        return entry.model_dump(mode="json")

    def entry_to_json(self, entry: KnowledgeEntry, pretty: bool = True) -> str:
        return json.dumps(self.entry_to_dict(entry), indent=2 if pretty else None)

    def entry_to_markdown(self, entry: KnowledgeEntry) -> str:
        """A simple, human-readable Markdown rendering of one entry -- for
        export/display, not a parsed or executed format."""
        lines = [
            f"# {entry.title}",
            "",
            f"**Category:** {entry.category.value} | **Difficulty:** {entry.difficulty.value}",
            "",
            entry.summary,
            "",
            entry.content,
        ]
        if entry.tags:
            lines += ["", f"**Tags:** {', '.join(entry.tags)}"]
        if entry.references:
            lines += ["", "**References:**"] + [f"- {r}" for r in entry.references]
        return "\n".join(lines)
