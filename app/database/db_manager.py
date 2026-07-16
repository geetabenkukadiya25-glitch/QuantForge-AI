"""
SQLite database connection management and schema initialization.

Phase 1 only establishes the connection layer and a `schema_version` table
used to track future migrations. Business tables (strategies, backtests,
optimization runs, etc.) are introduced by later phases via `models.py`.
"""

import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from app.config.paths import get_paths
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = 1


class DatabaseManager:
    """Owns the SQLite connection lifecycle for a single database file."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @property
    def db_path(self) -> Path:
        return self._db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection with sane defaults, committing on success."""
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create baseline schema (idempotent)."""
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version    INTEGER NOT NULL,
                    applied_at TEXT    NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            current = conn.execute(
                "SELECT MAX(version) AS version FROM schema_version"
            ).fetchone()["version"]

            if current is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                logger.info("Initialized database schema at version %s", SCHEMA_VERSION)
            else:
                logger.debug("Database schema already at version %s", current)


@lru_cache
def get_database_manager() -> DatabaseManager:
    """Return a cached singleton `DatabaseManager` bound to the configured path."""
    return DatabaseManager(get_paths().database_file)
