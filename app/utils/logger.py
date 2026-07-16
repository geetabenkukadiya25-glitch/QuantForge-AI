"""
Centralized logging system.

Every module should obtain its logger via `get_logger(__name__)` instead of
calling `logging.getLogger` directly, so log formatting, level, and output
targets stay controlled by a single configuration source (`Settings`).
"""

import logging
import sys
from functools import lru_cache
from logging.handlers import RotatingFileHandler

from app.config.paths import get_paths
from app.config.settings import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per log file
_BACKUP_COUNT = 5


@lru_cache
def _configure_root_logger() -> None:
    """Configure the root `quantforge` logger exactly once per process."""
    settings = get_settings()
    root = logging.getLogger("quantforge")
    root.setLevel(settings.log_level)
    root.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if settings.log_to_file:
        paths = get_paths()
        file_handler = RotatingFileHandler(
            paths.logs_dir / "quantforge.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger nested under the `quantforge` root logger."""
    _configure_root_logger()
    return logging.getLogger(f"quantforge.{name}")
