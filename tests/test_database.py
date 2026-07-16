"""Tests for the database initialization layer."""

from app.database.db_manager import DatabaseManager


def test_initialize_creates_schema_version_table(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)

    manager.initialize()

    assert db_path.exists()
    with manager.connect() as conn:
        row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
        assert row["version"] == 1


def test_initialize_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)

    manager.initialize()
    manager.initialize()

    with manager.connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM schema_version").fetchone()["n"]
        assert count == 1
