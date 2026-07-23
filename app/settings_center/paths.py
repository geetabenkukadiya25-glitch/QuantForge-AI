"""Managed-folder introspection and folder-opening for the Settings
Center (Phase 18.8). `list_managed_folders` reads `app.config.paths.Paths`
via `dataclasses.fields` (read-only) -- confirmed via the reuse audit
that `Paths` is `frozen=True` + `lru_cache`-singleton, so there is no
"change a folder at runtime" capability to hook into; override storage
lives on `SettingsState.path_overrides` (owned by `settings_manager.py`)
and is NOT consulted by `Paths`/`get_paths()` or any other module this
phase -- see Known Limitations. `open_folder` is a genuinely new,
previously-absent capability (confirmed zero prior art in the repo).
"""

import dataclasses
import subprocess
import sys
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


def list_managed_folders() -> list[dict]:
    from app.config.paths import get_paths

    paths = get_paths()
    return [{"key": f.name, "path": str(getattr(paths, f.name))} for f in dataclasses.fields(paths) if isinstance(getattr(paths, f.name), Path)]


def open_folder(path: Path | str) -> bool:
    """Best-effort "open in the OS file browser" -- never raises; returns
    `False` (and logs) on any failure so a caller can show an honest
    error instead of a silent no-op."""
    target = Path(path)
    try:
        if not target.exists():
            logger.warning("Cannot open folder '%s': it does not exist.", target)
            return False
        if sys.platform == "win32":
            import os

            os.startfile(target)  # noqa: S606 -- Windows-only, guarded by platform check
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True
    except OSError:
        logger.warning("Failed to open folder '%s'.", target, exc_info=True)
        return False
