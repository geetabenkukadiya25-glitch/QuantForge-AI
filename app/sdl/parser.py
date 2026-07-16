"""Parses raw YAML/JSON text (or files) into a plain strategy document dict.

`StrategyParser` only turns text into a dict -- it does not validate
structure or types (that is `StrategyValidator`'s job). Keeping parsing
and validation separate lets callers parse untrusted text safely and
inspect the raw dict before deciding whether to validate it.
"""

import json
from pathlib import Path
from typing import Any, Literal

import yaml

from app.sdl.exceptions import SDLParseError

SUPPORTED_FORMATS = ["yaml", "json"]
_FUTURE_FORMATS = ["toml"]

_EXTENSION_TO_FORMAT: dict[str, str] = {
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}


class StrategyParser:
    """Parses SDL documents from YAML or JSON text/files."""

    def parse_yaml(self, text: str) -> dict[str, Any]:
        """Parse YAML `text` into a dict.

        Raises:
            SDLParseError: if `text` is not valid YAML or is not a mapping.
        """
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SDLParseError(f"Invalid YAML: {exc}") from exc
        return self._require_mapping(data, "YAML")

    def parse_json(self, text: str) -> dict[str, Any]:
        """Parse JSON `text` into a dict.

        Raises:
            SDLParseError: if `text` is not valid JSON or is not an object.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SDLParseError(f"Invalid JSON: {exc}") from exc
        return self._require_mapping(data, "JSON")

    def parse(self, text: str, fmt: Literal["yaml", "json"]) -> dict[str, Any]:
        """Parse `text` in the given format.

        Raises:
            SDLParseError: if `fmt` is not a supported format, or parsing fails.
        """
        if fmt == "yaml":
            return self.parse_yaml(text)
        if fmt == "json":
            return self.parse_json(text)
        if fmt in _FUTURE_FORMATS:
            raise SDLParseError(f"Format {fmt!r} is a planned future format, not implemented yet.")
        raise SDLParseError(f"Unsupported format: {fmt!r}. Supported: {SUPPORTED_FORMATS}")

    def parse_file(self, file_path: str | Path) -> dict[str, Any]:
        """Parse a `.yaml`/`.yml`/`.json` file, inferring format from its extension.

        Raises:
            SDLParseError: if the file doesn't exist or has an unrecognized extension.
        """
        path = Path(file_path)
        if not path.exists():
            raise SDLParseError(f"Strategy file not found: {path}")

        fmt = _EXTENSION_TO_FORMAT.get(path.suffix.lower())
        if fmt is None:
            raise SDLParseError(
                f"Unrecognized strategy file extension: {path.suffix!r} ({path})"
            )
        return self.parse(path.read_text(encoding="utf-8"), fmt)  # type: ignore[arg-type]

    @staticmethod
    def _require_mapping(data: Any, fmt_name: str) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise SDLParseError(f"{fmt_name} document must be a mapping/object at the top level.")
        return data
