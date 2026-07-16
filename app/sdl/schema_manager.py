"""Introspection over the SDL schema.

`SchemaManager` is the single place that answers "what does the schema
look like" -- used by the validator (for required-section reporting), the
Streamlit UI (schema reference display), and generated documentation, so
none of them hardcode section/field lists themselves.
"""

from typing import Any

from app.sdl.models import SDL_SECTIONS, StrategyDefinition
from app.sdl.version import SDL_VERSION, SUPPORTED_SDL_VERSIONS

#: Sections that must be present (though some may legally be empty lists).
REQUIRED_SECTIONS: list[str] = ["metadata", "market", "symbols", "timeframes"]


class SchemaManager:
    """Read-only introspection over the current `StrategyDefinition` schema."""

    def get_sdl_version(self) -> str:
        """Return the SDL schema version this codebase implements."""
        return SDL_VERSION

    def get_supported_versions(self) -> list[str]:
        """Return every SDL version this codebase can validate against."""
        return list(SUPPORTED_SDL_VERSIONS)

    def get_sections(self) -> list[str]:
        """Return every top-level SDL section name, in schema order."""
        return list(SDL_SECTIONS)

    def get_required_sections(self) -> list[str]:
        """Return the top-level sections a strategy document must include."""
        return list(REQUIRED_SECTIONS)

    def get_json_schema(self) -> dict[str, Any]:
        """Return the full JSON Schema for `StrategyDefinition` (for docs/UI)."""
        return StrategyDefinition.model_json_schema()

    def describe_section(self, section: str) -> dict[str, Any]:
        """Return the JSON Schema fragment for a single top-level section.

        Raises:
            KeyError: if `section` is not a recognized SDL section.
        """
        if section not in SDL_SECTIONS:
            raise KeyError(f"Unknown SDL section: {section!r}. Known sections: {SDL_SECTIONS}")

        schema = self.get_json_schema()
        field_schema = schema["properties"][section]
        return {
            "section": section,
            "required": section in REQUIRED_SECTIONS,
            "schema": field_schema,
        }
