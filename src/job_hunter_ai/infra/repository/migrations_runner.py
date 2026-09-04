"""Applies the numbered SQL migrations shipped next to this module.

Hand-written versioned SQL, no Alembic — the rationale is in docs/DATA_MODEL.md.
"""

import sqlite3
from pathlib import Path

from job_hunter_ai.domain.time_utils import to_iso_utc, utc_now

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL
)
"""


def apply_migrations(connection: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> int:
    """Run every migration newer than the recorded version. Returns the resulting version."""
    connection.execute(_SCHEMA_VERSION_TABLE)
    current = _current_version(connection)
    for version, path in _pending(directory, current):
        connection.executescript(path.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, to_iso_utc(utc_now())),
        )
        current = version
    connection.commit()
    return current


def _current_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _pending(directory: Path, current: int) -> list[tuple[int, Path]]:
    found = [(int(path.name.split("_", 1)[0]), path) for path in directory.glob("[0-9]*_*.sql")]
    return sorted((item for item in found if item[0] > current), key=lambda item: item[0])
