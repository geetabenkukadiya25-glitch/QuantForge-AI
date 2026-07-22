"""Strategy Library management (Phase 18).

Transforms the Strategy Library from a read-only SDL viewer into a
complete offline strategy management system: new/duplicate/save/save-as/
rename/delete, import/export, search/filter, favorites, recently-opened,
validation badges, and local (git-free) version history.

UI and management ONLY -- this module never touches strategy execution,
Strategy Builder, the Backtesting/Validation/Replay/Research/Optimization/
Indicator Engines, or SDL parser/schema behavior. It composes
`app.sdl.StrategyParser` / `StrategyValidator` / `StrategySerializer`
exactly as they already exist.
"""

from app.strategy_library.exceptions import (
    DuplicateFilenameError,
    ProtectedStrategyError,
    StrategyFileNotFoundError,
    StrategyLibraryError,
    VersionNotFoundError,
)
from app.strategy_library.library_manager import StrategyLibraryManager
from app.strategy_library.models import (
    AuditEvent,
    AuditEventType,
    AutosaveRecord,
    CompileRecord,
    LibraryEntry,
    LibraryState,
    LockInfo,
    StrategySource,
    StrategyStatistics,
    Suggestion,
    ValidationBadge,
    VersionSnapshot,
)
from app.strategy_library.templates import list_template_names

__all__ = [
    "StrategyLibraryManager",
    "LibraryEntry",
    "LibraryState",
    "StrategySource",
    "ValidationBadge",
    "VersionSnapshot",
    "CompileRecord",
    "AutosaveRecord",
    "LockInfo",
    "AuditEvent",
    "AuditEventType",
    "StrategyStatistics",
    "Suggestion",
    "list_template_names",
    "StrategyLibraryError",
    "ProtectedStrategyError",
    "StrategyFileNotFoundError",
    "DuplicateFilenameError",
    "VersionNotFoundError",
]
