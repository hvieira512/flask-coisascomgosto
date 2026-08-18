"""Schema migrations: numbered .sql files, each applied once, in order.

    flask --app app migrate            apply whatever is pending
    flask --app app migrate --status   list what is applied and what is not

HOW THIS FITS WITH db/schema.sql
db/schema.sql stays the current state of the schema, and is what a fresh database
is built from — it is also the only place the whole shape is readable in one go.
A change therefore needs both halves:

    1. edit db/schema.sql, so new databases and the test suite get the change;
    2. add a file here, so the databases that already exist can catch up.

`init-db` builds from schema.sql and then *stamps* every migration as applied
without running it, because a database built from schema.sql is by definition
already current. That is what keeps the two halves from fighting: migrations only
ever run against a database that predates them.

WHAT THIS DOES NOT DO
There is no `down`. A migration that turns out to be wrong is corrected by
another migration, which is the only kind of undo that survives having already
run somewhere.

MySQL commits DDL implicitly, so a file mixing several ALTERs that fails partway
leaves the earlier ones applied and is not recorded — rerunning it would then hit
"column already exists". One logical change per file keeps that recoverable by
hand. Pure DML (an UPDATE, like renaming a lookup row) does roll back cleanly.
"""

from __future__ import annotations

from pathlib import Path

from db import _statements, get_db_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _ensure_table(cursor) -> None:
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  filename VARCHAR(255) NOT NULL PRIMARY KEY,"
        "  applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )


def available() -> list[Path]:
    """Every migration file, in the order they must run.

    Sorted by filename, which is why they are numbered: 0002 must not run before
    0010 just because "1" sorts before "2".
    """
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _applied(cursor) -> set[str]:
    _ensure_table(cursor)
    cursor.execute("SELECT filename FROM schema_migrations")
    return {row["filename"] for row in cursor.fetchall()}


def pending() -> list[Path]:
    with get_db_connection() as (_, cursor):
        done = _applied(cursor)
    return [path for path in available() if path.name not in done]


def status() -> list[tuple[str, bool]]:
    """(filename, applied) for every migration, in order."""
    with get_db_connection() as (_, cursor):
        done = _applied(cursor)
    return [(path.name, path.name in done) for path in available()]


def apply_pending() -> list[str]:
    """Run whatever has not run yet and return the filenames applied.

    One connection per file: the record of a migration lands in the same commit
    as the migration itself wherever MySQL allows it, so a failure cannot leave a
    file marked as applied.
    """
    applied = []
    for path in pending():
        statements = _statements(path.read_text(encoding="utf-8"))
        with get_db_connection() as (_, cursor):
            for statement in statements:
                cursor.execute(statement)
            cursor.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
            )
        applied.append(path.name)
    return applied


def stamp_all() -> int:
    """Record every migration as applied without running any of it.

    For a database just built from schema.sql, which already contains everything
    the migrations would do. Returns how many were newly stamped.
    """
    names = [path.name for path in available()]
    if not names:
        return 0

    with get_db_connection() as (_, cursor):
        _ensure_table(cursor)
        # IGNORE, so stamping twice is not an error: init-db is re-runnable.
        cursor.executemany(
            "INSERT IGNORE INTO schema_migrations (filename) VALUES (%s)",
            [(name,) for name in names],
        )
        return cursor.rowcount
