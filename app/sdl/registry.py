"""Filesystem-backed storage for strategy documents.

`StrategyRegistry` is the single place strategies are saved, loaded,
searched, and deleted -- composing `StrategyParser`, `StrategyValidator`,
and `StrategySerializer` rather than reimplementing any of their logic
(no duplicate business logic, per `PROJECT_VISION.md`).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config.paths import get_paths
from app.sdl.exceptions import SDLRegistryError, SDLValidationError
from app.sdl.models import StrategyDefinition
from app.sdl.parser import StrategyParser
from app.sdl.serializer import StrategySerializer
from app.sdl.validator import StrategyValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)

_EXTENSION_BY_FORMAT = {"yaml": ".yaml", "json": ".json"}


@dataclass
class StrategySummary:
    """Lightweight metadata for listing/search results (no full document)."""

    id: str
    name: str
    category: str | None
    tags: list[str]
    sdl_version: str
    strategy_version: str
    file_path: Path


class StrategyRegistry:
    """CRUD storage for `StrategyDefinition` documents on disk."""

    def __init__(
        self,
        library_dir: Path | None = None,
        parser: StrategyParser | None = None,
        validator: StrategyValidator | None = None,
        serializer: StrategySerializer | None = None,
    ) -> None:
        self._dir = library_dir or get_paths().sdl_library_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._parser = parser or StrategyParser()
        self._validator = validator or StrategyValidator()
        self._serializer = serializer or StrategySerializer()

    def save(
        self,
        definition: StrategyDefinition,
        fmt: Literal["yaml", "json"] = "yaml",
        overwrite: bool = False,
    ) -> Path:
        """Persist `definition` to the registry.

        Raises:
            SDLRegistryError: if a file for this strategy id already exists
                and `overwrite` is False.
        """
        path = self._path_for(definition.metadata.id, fmt)
        if path.exists() and not overwrite:
            raise SDLRegistryError(
                f"Strategy '{definition.metadata.id}' already exists at {path}. "
                "Pass overwrite=True to replace it."
            )

        text = (
            self._serializer.to_yaml(definition)
            if fmt == "yaml"
            else self._serializer.to_json(definition)
        )
        path.write_text(text, encoding="utf-8")
        logger.info("Saved strategy '%s' to %s", definition.metadata.id, path)
        return path

    def load(self, strategy_id: str) -> StrategyDefinition:
        """Load and validate the strategy with the given id.

        Raises:
            SDLRegistryError: if no file exists for `strategy_id`.
            SDLValidationError: if the stored document is no longer valid.
        """
        path = self._find_path(strategy_id)
        data = self._parser.parse_file(path)
        result = self._validator.validate(data)
        if not result.is_valid:
            raise SDLValidationError(result.errors)
        assert result.definition is not None
        return result.definition

    def delete(self, strategy_id: str) -> None:
        """Delete the stored strategy with the given id.

        Raises:
            SDLRegistryError: if no file exists for `strategy_id`.
        """
        path = self._find_path(strategy_id)
        path.unlink()
        logger.info("Deleted strategy '%s' (%s)", strategy_id, path)

    def list(self) -> list[StrategySummary]:
        """Return summaries for every strategy in the registry."""
        summaries: list[StrategySummary] = []
        for path in sorted(self._dir.glob("*")):
            if path.suffix.lower() not in (".yaml", ".yml", ".json"):
                continue
            try:
                data = self._parser.parse_file(path)
                result = self._validator.validate(data)
            except Exception as exc:  # a corrupt file shouldn't break listing everything else
                logger.warning("Skipping unreadable strategy file %s: %s", path, exc)
                continue
            if result.definition is None:
                logger.warning("Skipping invalid strategy file %s", path)
                continue
            summaries.append(self._summarize(result.definition, path))
        return summaries

    def search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> list[StrategySummary]:
        """Return summaries matching a free-text name/id query, tags, and/or category."""
        results = self.list()
        if query:
            needle = query.lower()
            results = [s for s in results if needle in s.name.lower() or needle in s.id.lower()]
        if tags:
            wanted = set(tags)
            results = [s for s in results if wanted.issubset(set(s.tags))]
        if category:
            results = [s for s in results if s.category == category]
        return results

    def import_file(self, file_path: str | Path, overwrite: bool = False) -> StrategyDefinition:
        """Parse, validate, and save an external strategy file into the registry.

        Raises:
            SDLValidationError: if the file's document fails validation.
        """
        data = self._parser.parse_file(file_path)
        result = self._validator.validate(data)
        if not result.is_valid:
            raise SDLValidationError(result.errors)
        assert result.definition is not None
        self.save(result.definition, overwrite=overwrite)
        return result.definition

    def export(
        self, strategy_id: str, dest_path: str | Path, fmt: Literal["yaml", "json"] = "yaml"
    ) -> Path:
        """Load a strategy from the registry and write it to an external path."""
        definition = self.load(strategy_id)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = (
            self._serializer.to_yaml(definition)
            if fmt == "yaml"
            else self._serializer.to_json(definition)
        )
        dest.write_text(text, encoding="utf-8")
        logger.info("Exported strategy '%s' to %s", strategy_id, dest)
        return dest

    def _path_for(self, strategy_id: str, fmt: Literal["yaml", "json"]) -> Path:
        return self._dir / f"{strategy_id}{_EXTENSION_BY_FORMAT[fmt]}"

    def _find_path(self, strategy_id: str) -> Path:
        for extension in (".yaml", ".yml", ".json"):
            candidate = self._dir / f"{strategy_id}{extension}"
            if candidate.exists():
                return candidate
        raise SDLRegistryError(f"No strategy found with id {strategy_id!r} in {self._dir}")

    @staticmethod
    def _summarize(definition: StrategyDefinition, path: Path) -> StrategySummary:
        return StrategySummary(
            id=definition.metadata.id,
            name=definition.metadata.name,
            category=definition.metadata.category,
            tags=list(definition.tags),
            sdl_version=definition.metadata.sdl_version,
            strategy_version=definition.metadata.strategy_version,
            file_path=path,
        )
