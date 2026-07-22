"""Strategy Library management orchestrator (Phase 18).

`StrategyLibraryManager` turns the read-only bundled `app/sdl/examples/`
viewer into a full offline strategy management system: new/duplicate/
save/save-as/rename/delete, import/export, search/filter, favorites,
recently-opened, validation badges, and local (git-free) version history.

It is a pure orchestration + file-management layer -- it NEVER
reimplements parsing, validation, or serialization (always delegates to
`app.sdl.StrategyParser` / `StrategyValidator` / `StrategySerializer`) and
NEVER touches strategy execution, the Strategy Builder, or any other
engine. Two directories are never mixed:

- `app/sdl/examples/` -- bundled, built-in, always protected (read + copy
  only, via `duplicate`/`export_text`; never overwritten, deleted, or
  renamed in place).
- `app/sdl/library/` (`Paths.sdl_library_dir`) -- the user's own saved
  strategies; every mutating operation (`save`, `rename`, `delete`, ...)
  only ever writes here.

Favorites/recent/version-history are local, file-based state (a single
JSON document under `Paths.sdl_library_state_dir`) -- no database, no
network, consistent with the rest of the offline platform.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.config.paths import get_paths
from app.sdl.exceptions import SDLValidationError
from app.sdl.models import Market, Metadata, StrategyDefinition
from app.sdl.parser import StrategyParser
from app.sdl.serializer import StrategySerializer
from app.sdl.validator import StrategyValidator
from app.strategy_library.audit_log import AuditLogStore
from app.strategy_library.autosave import AutosaveStore
from app.strategy_library.compile_status import CompileStatusStore
from app.strategy_library.exceptions import (
    DuplicateFilenameError,
    ProtectedStrategyError,
    StrategyFileNotFoundError,
    VersionNotFoundError,
)
from app.strategy_library.lock import LockStore
from app.strategy_library.models import (
    AuditEvent,
    AuditEventType,
    AutosaveRecord,
    CompileRecord,
    LibraryEntry,
    LibraryState,
    StrategySource,
    StrategyStatistics,
    Suggestion,
    ValidationBadge,
    VersionSnapshot,
)
from app.strategy_library.statistics import compute_statistics
from app.strategy_library.suggestions import compute_suggestions
from app.strategy_library.templates import build_template
from app.utils.logger import get_logger

logger = get_logger(__name__)

_STRATEGY_EXTENSIONS = (".yaml", ".yml", ".json")
_EXT_BY_FORMAT = {"yaml": ".yaml", "json": ".json"}
_MAX_RECENT = 10
_MAX_VERSIONS_PER_STRATEGY = 20


class StrategyLibraryManager:
    """CRUD + search/filter/favorites/recent/version-history over
    strategy files, keeping built-in examples strictly read-only."""

    def __init__(
        self,
        examples_dir: Path | None = None,
        user_dir: Path | None = None,
        state_dir: Path | None = None,
        autosave_dir: Path | None = None,
        root: Path | None = None,
        parser: StrategyParser | None = None,
        validator: StrategyValidator | None = None,
        serializer: StrategySerializer | None = None,
    ) -> None:
        paths = get_paths()
        self._examples_dir = examples_dir or paths.sdl_examples_dir
        self._user_dir = user_dir or paths.sdl_library_dir
        self._state_dir = state_dir or paths.sdl_library_state_dir
        self._autosave_dir = autosave_dir or paths.sdl_autosave_dir
        self._root = root or paths.root
        self._user_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._parser = parser or StrategyParser()
        self._validator = validator or StrategyValidator()
        self._serializer = serializer or StrategySerializer()

        self._compile_status = CompileStatusStore(self._state_dir)
        self._autosave = AutosaveStore(self._autosave_dir)
        self._locks = LockStore(self._state_dir)
        self._audit_log = AuditLogStore(self._state_dir)

    # ------------------------------------------------------------------
    # Listing / browsing
    # ------------------------------------------------------------------

    def list_entries(self) -> list[LibraryEntry]:
        """Every strategy in both the examples and user library, favorites first."""
        state = self._load_state()
        entries = [self._build_entry(p, StrategySource.EXAMPLE, state) for p in self._iter_files(self._examples_dir)]
        entries += [self._build_entry(p, StrategySource.USER, state) for p in self._iter_files(self._user_dir)]
        entries.sort(key=lambda e: (not e.is_favorite, e.name.lower()))
        return entries

    def get_entry(self, path: Path) -> LibraryEntry:
        path = Path(path)
        if not path.exists():
            raise StrategyFileNotFoundError(f"No strategy file at {path}")
        source = StrategySource.EXAMPLE if self.is_protected(path) else StrategySource.USER
        return self._build_entry(path, source, self._load_state())

    def is_protected(self, path: Path) -> bool:
        """True if `path` is inside the bundled, read-only examples directory."""
        try:
            Path(path).resolve().relative_to(self._examples_dir.resolve())
            return True
        except ValueError:
            return False

    def search(self, entries: list[LibraryEntry], query: str) -> list[LibraryEntry]:
        """Live free-text search over name / id / author / tags / category."""
        needle = (query or "").strip().lower()
        if not needle:
            return entries

        def matches(entry: LibraryEntry) -> bool:
            haystacks = [entry.name, entry.strategy_id, entry.author or "", entry.category or "", *entry.tags]
            return any(needle in h.lower() for h in haystacks)

        return [e for e in entries if matches(e)]

    def filter_entries(self, entries: list[LibraryEntry], selected: list[str]) -> list[LibraryEntry]:
        """Filter by any of asset class / category / tag (e.g. "Forex", "SMC",
        "Breakout") -- an entry matches if it carries ANY selected chip."""
        if not selected:
            return entries
        wanted = {s.lower() for s in selected}

        def matches(entry: LibraryEntry) -> bool:
            haystack = {t.lower() for t in entry.tags}
            if entry.category:
                haystack.add(entry.category.lower())
            if entry.asset_class:
                haystack.add(entry.asset_class.lower())
            return bool(wanted & haystack)

        return [e for e in entries if matches(e)]

    # ------------------------------------------------------------------
    # Loading raw content / definitions
    # ------------------------------------------------------------------

    def load_definition(self, path: Path) -> StrategyDefinition:
        """Parse + validate `path`. Raises `SDLParseError`/`SDLValidationError`."""
        raw = self._parser.parse_file(path)
        result = self._validator.validate(raw)
        if not result.is_valid:
            raise SDLValidationError(result.errors)
        assert result.definition is not None
        return result.definition

    def load_text(self, path: Path) -> str:
        """The strategy file's raw on-disk text, for the editor."""
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def detect_format(path: Path) -> Literal["yaml", "json"]:
        return "json" if Path(path).suffix.lower() == ".json" else "yaml"

    # ------------------------------------------------------------------
    # New / Duplicate / Save / Save As
    # ------------------------------------------------------------------

    def new_strategy(
        self, filename: str, name: str, author: str | None = None, fmt: Literal["yaml", "json"] = "yaml"
    ) -> Path:
        """Create a blank SDL template with sensible, schema-valid minimum
        defaults (a strategy document cannot omit `market`/`symbols`/
        `timeframes` -- these are required by the unmodified SDL schema)
        and save it to the user library."""
        strategy_id = self._unique_id(self._slugify(Path(filename).stem or name))
        definition = StrategyDefinition(
            metadata=Metadata(id=strategy_id, name=name, author=author, created_at=datetime.now(timezone.utc)),
            market=Market(asset_class="forex"),
            symbols=["UNKNOWN"],
            timeframes=["M15"],
        )
        saved_path = self.save(definition, filename, fmt=fmt, overwrite=False, note="Created")
        self._audit_log.record(AuditEventType.CREATED, self._state_key(saved_path))
        return saved_path

    def new_strategy_from_template(
        self,
        template_name: str,
        filename: str,
        name: str,
        author: str | None = None,
        fmt: Literal["yaml", "json"] = "yaml",
    ) -> Path:
        """Create a new strategy pre-filled from a named template (Phase 18
        rule 20). Raises `KeyError` for an unknown `template_name`."""
        strategy_id = self._unique_id(self._slugify(Path(filename).stem or name))
        definition = build_template(template_name, strategy_id, name, author)
        saved_path = self.save(definition, filename, fmt=fmt, overwrite=False, note=f"Created from template '{template_name}'")
        self._audit_log.record(AuditEventType.CREATED, self._state_key(saved_path))
        return saved_path

    def duplicate(self, path: Path) -> tuple[StrategyDefinition, str, Literal["yaml", "json"]]:
        """Build (but do not save) a duplicate of the strategy at `path`:
        same content, a new unique id, and a suggested `<name>_copy`
        filename -- so the caller can let the user rename before saving.
        Works on both examples and user strategies (duplicating FROM an
        example is how a protected strategy becomes an editable copy);
        the suggested filename always targets the user library."""
        definition = self.load_definition(path)
        fmt = self.detect_format(path)
        new_id = self._unique_id(f"{definition.metadata.id}-copy")
        duplicated = definition.model_copy(
            update={"metadata": definition.metadata.model_copy(update={"id": new_id, "created_at": datetime.now(timezone.utc)})}
        )
        suggested_filename = self._unique_filename(f"{Path(path).stem}_copy", fmt)
        return duplicated, suggested_filename, fmt

    def save(
        self,
        definition: StrategyDefinition,
        filename: str,
        fmt: Literal["yaml", "json"] = "yaml",
        overwrite: bool = True,
        note: str = "",
    ) -> Path:
        """Write `definition` into the user library as `filename`.

        Raises:
            SDLValidationError: if `definition` fails validation (defensive --
                never persist an invalid document).
            ProtectedStrategyError: if `filename` would resolve inside the
                examples directory (should not happen via the UI; guarded here too).
            DuplicateFilenameError: if the file exists and `overwrite` is False.
        """
        result = self._validator.validate(definition)
        if not result.is_valid:
            raise SDLValidationError(result.errors)

        filename = self._ensure_extension(filename, fmt)
        target = self._user_dir / filename
        if self.is_protected(target):
            raise ProtectedStrategyError("Built-in examples cannot be overwritten. Use Save As.")
        existed_before = target.exists()
        if existed_before and not overwrite:
            raise DuplicateFilenameError(f"'{filename}' already exists. Choose a different name or confirm overwrite.")

        text = self._serializer.to_yaml(definition) if fmt == "yaml" else self._serializer.to_json(definition)
        target.write_text(text, encoding="utf-8")
        self._record_version(target, fmt, text, note or ("Updated" if existed_before else "Created"))
        self._audit_log.record(AuditEventType.SAVED, self._state_key(target))
        logger.info("Saved strategy '%s' to %s", definition.metadata.id, target)
        return target

    def save_as(self, definition: StrategyDefinition, filename: str, fmt: Literal["yaml", "json"] = "yaml") -> Path:
        """Save to a new file without modifying/overwriting anything else."""
        return self.save(definition, filename, fmt=fmt, overwrite=False, note="Saved As")

    # ------------------------------------------------------------------
    # Rename / Delete
    # ------------------------------------------------------------------

    def rename(self, path: Path, new_filename: str, new_id: str | None = None, new_name: str | None = None) -> Path:
        path = Path(path)
        if self.is_protected(path):
            raise ProtectedStrategyError("Built-in examples cannot be renamed. Use Save As to create your own copy.")

        definition = self.load_definition(path)
        fmt = self.detect_format(path)
        new_filename = self._ensure_extension(new_filename, fmt)
        target = self._user_dir / new_filename
        if target != path and target.exists():
            raise DuplicateFilenameError(f"'{new_filename}' already exists.")

        meta_updates = {k: v for k, v in {"id": new_id, "name": new_name}.items() if v}
        renamed_definition = (
            definition.model_copy(update={"metadata": definition.metadata.model_copy(update=meta_updates)})
            if meta_updates
            else definition
        )
        text = self._serializer.to_yaml(renamed_definition) if fmt == "yaml" else self._serializer.to_json(renamed_definition)
        target.write_text(text, encoding="utf-8")

        if target != path:
            self._migrate_state_key(path, target)
            self._compile_status.rename_key(self._state_key(path), self._state_key(target))
            path.unlink()
        self._record_version(target, fmt, text, "Renamed")
        logger.info("Renamed strategy %s -> %s", path, target)
        return target

    def delete(self, path: Path) -> None:
        path = Path(path)
        if self.is_protected(path):
            raise ProtectedStrategyError("This strategy is protected.")
        if not path.exists():
            raise StrategyFileNotFoundError(f"No strategy file at {path}")

        key = self._state_key(path)
        path.unlink()
        state = self._load_state()
        state.favorites = [k for k in state.favorites if k != key]
        state.recent = [k for k in state.recent if k != key]
        state.versions.pop(key, None)
        self._save_state(state)
        self._compile_status.clear(key)
        self._audit_log.record(AuditEventType.DELETED, key)
        logger.info("Deleted user strategy %s", path)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def import_file(self, source_path: Path, filename: str | None = None, overwrite: bool = False) -> Path:
        """Parse + validate an external `.yaml`/`.yml`/`.json` file and save
        it into the user library. Raises `SDLParseError`/`SDLValidationError`
        (never silently imports an invalid document)."""
        source_path = Path(source_path)
        raw = self._parser.parse_file(source_path)
        result = self._validator.validate(raw)
        if not result.is_valid:
            raise SDLValidationError(result.errors)
        assert result.definition is not None
        fmt = self.detect_format(source_path)
        target_filename = filename or source_path.name
        saved_path = self.save(result.definition, target_filename, fmt=fmt, overwrite=overwrite, note="Imported")
        self._audit_log.record(AuditEventType.IMPORTED, self._state_key(saved_path))
        return saved_path

    def export_text(self, path: Path, fmt: Literal["yaml", "json"]) -> str:
        """The strategy's content re-serialized in the requested format
        (independent of how it's stored on disk) -- for a download button."""
        definition = self.load_definition(path)
        self._audit_log.record(AuditEventType.EXPORTED, self._state_key(path))
        return self._serializer.to_yaml(definition) if fmt == "yaml" else self._serializer.to_json(definition)

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def is_favorite(self, path: Path) -> bool:
        return self._state_key(path) in self._load_state().favorites

    def toggle_favorite(self, path: Path) -> bool:
        """Flip favorite status; returns the new state."""
        state = self._load_state()
        key = self._state_key(path)
        if key in state.favorites:
            state.favorites.remove(key)
            is_now_favorite = False
        else:
            state.favorites.append(key)
            is_now_favorite = True
        self._save_state(state)
        return is_now_favorite

    # ------------------------------------------------------------------
    # Recent
    # ------------------------------------------------------------------

    def record_recent(self, path: Path) -> None:
        state = self._load_state()
        key = self._state_key(path)
        state.recent = ([key] + [k for k in state.recent if k != key])[:_MAX_RECENT]
        self._save_state(state)

    def list_recent(self) -> list[Path]:
        state = self._load_state()
        return [p for p in (self._path_from_key(k) for k in state.recent) if p.exists()]

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------

    def list_versions(self, path: Path) -> list[VersionSnapshot]:
        return list(self._load_state().versions.get(self._state_key(path), []))

    def restore_version(self, path: Path, version_id: int) -> Path:
        path = Path(path)
        if self.is_protected(path):
            raise ProtectedStrategyError("Built-in examples cannot be modified. Use Save As.")

        snapshot = next((s for s in self.list_versions(path) if s.version_id == version_id), None)
        if snapshot is None:
            raise VersionNotFoundError(f"No version {version_id} for {path}")

        raw = self._parser.parse(snapshot.content, snapshot.fmt)
        result = self._validator.validate(raw)
        if not result.is_valid:
            raise SDLValidationError(result.errors)

        path.write_text(snapshot.content, encoding="utf-8")
        self._record_version(path, snapshot.fmt, snapshot.content, f"Restored from version {version_id}")
        logger.info("Restored %s to version %d", path, version_id)
        return path

    # ------------------------------------------------------------------
    # Validation badge
    # ------------------------------------------------------------------

    def validation_badge(self, path: Path) -> ValidationBadge:
        return self.get_entry(path).validation_badge

    def record_validated(self, path: Path) -> None:
        self._audit_log.record(AuditEventType.VALIDATED, self._state_key(path))

    # ------------------------------------------------------------------
    # Compile status (rule 22)
    # ------------------------------------------------------------------

    def record_compile_result(self, path: Path, success: bool, duration_seconds: float, error_message: str | None = None) -> None:
        """Record the outcome of a `StrategyCompiler.compile()` attempt the
        caller already ran -- this module never calls the compiler itself."""
        key = self._state_key(path)
        self._compile_status.record(key, CompileRecord(compiled_at=datetime.now(timezone.utc), success=success, duration_seconds=duration_seconds, error_message=error_message))
        self._audit_log.record(AuditEventType.COMPILED, key)

    def get_compile_status(self, path: Path) -> CompileRecord | None:
        """`None` means "Never Compiled"."""
        return self._compile_status.get(self._state_key(path))

    # ------------------------------------------------------------------
    # Autosave / Recovery (rules 26 & 27)
    # ------------------------------------------------------------------

    def autosave(self, path: Path | None, session_token: str, fmt: Literal["yaml", "json"], content: str) -> AutosaveRecord:
        """Snapshot `content` under `Paths.sdl_autosave_dir` ONLY -- never
        touches `path` itself. `path=None` covers a new, not-yet-saved
        strategy (keyed by `session_token` instead)."""
        original_key = self._state_key(path) if path is not None else None
        return self._autosave.save(original_key, session_token, fmt, content)

    def get_autosave(self, path: Path | None, session_token: str) -> AutosaveRecord | None:
        original_key = self._state_key(path) if path is not None else None
        return self._autosave.get(original_key, session_token)

    def discard_autosave(self, path: Path | None, session_token: str) -> None:
        original_key = self._state_key(path) if path is not None else None
        self._autosave.discard(original_key, session_token)

    def state_key(self, path: Path) -> str:
        """The stable, portable key `LibraryState`/audit/autosave/compile
        status use to identify a strategy file -- the public counterpart
        to the internal `_state_key`."""
        return self._state_key(path)

    def path_from_state_key(self, key: str) -> Path:
        """Resolve a `LibraryState`/audit/autosave key back to a filesystem
        path -- the public counterpart to the internal `_state_key`, for
        callers (e.g. the UI) that only have the key on hand."""
        return self._path_from_key(key)

    def list_recoverable_autosaves(self) -> list[AutosaveRecord]:
        """Every autosave on disk whose content differs from its original
        strategy's current on-disk content (or that has no original --
        i.e. it was a new, never-saved strategy) -- what the UI should
        offer as "Recovered Strategy Found" at startup."""
        recoverable = []
        for record in self._autosave.list_all():
            if record.original_key is None:
                recoverable.append(record)
                continue
            original_path = self._path_from_key(record.original_key)
            if not original_path.exists() or original_path.read_text(encoding="utf-8") != record.content:
                recoverable.append(record)
        return recoverable

    # ------------------------------------------------------------------
    # File lock protection (rule 28)
    # ------------------------------------------------------------------

    def acquire_lock(self, path: Path, owner_token: str) -> bool:
        return self._locks.acquire(self._state_key(path), owner_token)

    def release_lock(self, path: Path, owner_token: str) -> None:
        self._locks.release(self._state_key(path), owner_token)

    def heartbeat_lock(self, path: Path, owner_token: str) -> None:
        self._locks.heartbeat(self._state_key(path), owner_token)

    def is_locked_by_other(self, path: Path, owner_token: str) -> bool:
        return self._locks.is_locked_by_other(self._state_key(path), owner_token)

    # ------------------------------------------------------------------
    # Statistics / Suggestions (rules 23 & 24)
    # ------------------------------------------------------------------

    def compute_statistics(self, path: Path) -> StrategyStatistics:
        definition = self.load_definition(path)
        return compute_statistics(definition, self.load_text(path))

    def compute_suggestions(self, path: Path) -> list[Suggestion]:
        definition = self.load_definition(path)
        return compute_suggestions(definition)

    # ------------------------------------------------------------------
    # Audit log (rule 29)
    # ------------------------------------------------------------------

    def record_opened(self, path: Path) -> None:
        self._audit_log.record(AuditEventType.OPENED, self._state_key(path))

    def record_edited(self, path: Path | None, session_token: str) -> None:
        self._audit_log.record(AuditEventType.EDITED, self._state_key(path) if path is not None else f"__new__:{session_token}")

    def list_audit_events(self, path: Path | None = None, limit: int = 200) -> list[AuditEvent]:
        return self._audit_log.list_events(self._state_key(path) if path is not None else None, limit=limit)

    # ------------------------------------------------------------------
    # Internal: entry building
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_files(directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(p for p in directory.glob("*") if p.suffix.lower() in _STRATEGY_EXTENSIONS)

    def _build_entry(self, path: Path, source: StrategySource, state: LibraryState) -> LibraryEntry:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        is_favorite = self._state_key(path) in state.favorites

        try:
            raw = self._parser.parse_file(path)
        except Exception as exc:  # a corrupt/unreadable file must not break listing everything else
            return self._invalid_entry(path, source, modified_at, is_favorite, f"Could not parse: {exc}")

        result = self._validator.validate(raw)
        definition = result.definition
        if definition is None:
            summary = "; ".join(str(e) for e in result.errors) or "Invalid structure."
            name = str(raw.get("metadata", {}).get("name") or path.stem) if isinstance(raw, dict) else path.stem
            strategy_id = str(raw.get("metadata", {}).get("id") or path.stem) if isinstance(raw, dict) else path.stem
            return self._invalid_entry(path, source, modified_at, is_favorite, summary, name=name, strategy_id=strategy_id)

        badge = (
            ValidationBadge.VALID
            if result.is_valid and not result.warnings
            else (ValidationBadge.WARNING if result.is_valid else ValidationBadge.INVALID)
        )
        md = definition.metadata
        risk = definition.risk_management
        risk_parts = []
        if risk is not None:
            if risk.max_risk_per_trade_pct is not None:
                risk_parts.append(f"Risk/trade: {risk.max_risk_per_trade_pct}%")
            if risk.max_open_positions is not None:
                risk_parts.append(f"Max positions: {risk.max_open_positions}")

        return LibraryEntry(
            path=path,
            filename=path.name,
            source=source,
            strategy_id=md.id,
            name=md.name,
            strategy_version=md.strategy_version,
            sdl_version=md.sdl_version,
            author=md.author,
            category=md.category,
            tags=tuple(definition.tags),
            asset_class=definition.market.asset_class,
            market_type=definition.market.market_type,
            symbols=tuple(definition.symbols),
            timeframes=tuple(definition.timeframes),
            primary_timeframe=definition.primary_timeframe,
            sessions=tuple(definition.sessions),
            indicator_names=tuple(i.name for i in definition.indicators),
            execution_type=definition.execution_rules.order_type if definition.execution_rules else None,
            risk_model_summary=", ".join(risk_parts) or None,
            created_at=md.created_at,
            modified_at=modified_at,
            validation_badge=badge,
            validation_summary=result.report(),
            is_favorite=is_favorite,
            description=md.description,
            entry_rule_conditions=tuple(r.condition for r in definition.entry_rules),
            exit_rule_conditions=tuple(r.condition for r in definition.exit_rules),
        )

    @staticmethod
    def _invalid_entry(
        path: Path,
        source: StrategySource,
        modified_at: datetime,
        is_favorite: bool,
        summary: str,
        name: str | None = None,
        strategy_id: str | None = None,
    ) -> LibraryEntry:
        return LibraryEntry(
            path=path,
            filename=path.name,
            source=source,
            strategy_id=strategy_id or path.stem,
            name=name or path.stem,
            strategy_version="-",
            sdl_version="-",
            author=None,
            category=None,
            tags=(),
            asset_class=None,
            market_type=None,
            symbols=(),
            timeframes=(),
            primary_timeframe=None,
            sessions=(),
            indicator_names=(),
            execution_type=None,
            risk_model_summary=None,
            created_at=None,
            modified_at=modified_at,
            validation_badge=ValidationBadge.INVALID,
            validation_summary=summary,
            is_favorite=is_favorite,
        )

    # ------------------------------------------------------------------
    # Internal: naming
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug or "strategy"

    def _unique_id(self, candidate: str) -> str:
        existing_ids = {e.strategy_id for e in self.list_entries()}
        if candidate not in existing_ids:
            return candidate
        n = 2
        while f"{candidate}-{n}" in existing_ids:
            n += 1
        return f"{candidate}-{n}"

    def _unique_filename(self, stem: str, fmt: Literal["yaml", "json"]) -> str:
        ext = _EXT_BY_FORMAT[fmt]
        candidate = f"{stem}{ext}"
        n = 2
        while (self._user_dir / candidate).exists():
            candidate = f"{stem}_{n}{ext}"
            n += 1
        return candidate

    @staticmethod
    def _ensure_extension(filename: str, fmt: Literal["yaml", "json"]) -> str:
        if Path(filename).suffix.lower() in _STRATEGY_EXTENSIONS:
            return filename
        return filename + _EXT_BY_FORMAT[fmt]

    # ------------------------------------------------------------------
    # Internal: local state (favorites / recent / version history)
    # ------------------------------------------------------------------

    def _state_key(self, path: Path) -> str:
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(self._root.resolve()).as_posix()
        except ValueError:
            return resolved.as_posix()

    def _path_from_key(self, key: str) -> Path:
        candidate = Path(key)
        return candidate if candidate.is_absolute() else self._root / key

    def _migrate_state_key(self, old_path: Path, new_path: Path) -> None:
        old_key, new_key = self._state_key(old_path), self._state_key(new_path)
        state = self._load_state()
        if old_key in state.versions:
            state.versions[new_key] = state.versions.pop(old_key)
        state.favorites = [new_key if k == old_key else k for k in state.favorites]
        state.recent = [new_key if k == old_key else k for k in state.recent]
        self._save_state(state)

    def _record_version(self, path: Path, fmt: str, content: str, note: str) -> None:
        state = self._load_state()
        key = self._state_key(path)
        existing = state.versions.get(key, [])
        next_id = (existing[-1].version_id + 1) if existing else 1
        snapshot = VersionSnapshot(version_id=next_id, saved_at=datetime.now(timezone.utc), fmt=fmt, content=content, note=note)
        state.versions[key] = (existing + [snapshot])[-_MAX_VERSIONS_PER_STRATEGY:]
        self._save_state(state)

    def _state_file(self) -> Path:
        return self._state_dir / "library_state.json"

    def _load_state(self) -> LibraryState:
        file = self._state_file()
        if not file.exists():
            return LibraryState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Strategy library state file is unreadable; starting fresh.")
            return LibraryState()
        return LibraryState.from_dict(data)

    def _save_state(self, state: LibraryState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
