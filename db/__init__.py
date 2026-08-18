"""The database: connecting to it, and creating it.

This is not part of the REST API — the storefront's page routes, the seed and the
CLI all read through the same repositories — so it lives beside the schema it
builds rather than under api/.

    db/__init__.py   connect, get_db_connection, init_db
    db/migrate.py    the migration runner behind `flask migrate`
    db/schema.sql    the current schema, and what init_db builds
    db/migrations/   numbered .sql files, each applied once
    db/seed.py       development data
"""

import re
import time
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

from config import Config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(*, database=True):
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE if database else None,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


class _Connection:
    def __init__(self):
        self._conn = connect()
        self.cursor = self._conn.cursor()

    def __enter__(self):
        return self._conn, self.cursor

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self.cursor.close()
            self._conn.close()
        return False


def get_db_connection():
    """Yield a (connection, cursor) pair, committing on success."""
    return _Connection()


def _statements(schema):
    # Line comments are stripped first: a semicolon inside one would otherwise
    # cut a statement in half.
    return [s.strip() for s in re.sub(r"--[^\n]*", "", schema).split(";") if s.strip()]


def wait_for_mysql(timeout=60):
    """The compose healthcheck only covers `docker compose up`; init-db and the
    test runner start outside that ordering."""
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            connect(database=False).close()
            return
        except pymysql.Error as error:
            last_error = error
            time.sleep(1)

    raise RuntimeError(f"MySQL not reachable after {timeout}s: {last_error}")


def _read_users(cursor):
    """The accounts as they stand, or nothing if there is no table yet."""
    try:
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()
    except pymysql.Error:
        return []


def _restore_users(cursor, rows):
    """Put the saved accounts back after the schema has been recreated.

    Only the columns the new users table actually has: a schema change that adds
    or drops one must not be the thing that loses the accounts. Ids come back
    with them, so anything referring to a user still points at the same person.
    """
    if not rows:
        return 0

    cursor.execute("SHOW COLUMNS FROM users")
    columns = [row["Field"] for row in cursor.fetchall()]

    restored = 0
    for row in rows:
        keep = {c: row[c] for c in columns if c in row}
        if not keep:
            continue
        names = ", ".join(f"`{c}`" for c in keep)
        placeholders = ", ".join(["%s"] * len(keep))
        cursor.execute(
            f"INSERT INTO users ({names}) VALUES ({placeholders})", list(keep.values())
        )
        restored += 1
    return restored


def init_db(*, keep_users=True):
    """(Re)create the database and every table, dropping what is there.

    The accounts survive by default. schema.sql drops every table and seeds only
    the catalog's own lookups, so re-running this to pick up a schema change used
    to silently log the owners out of their own dashboard with no way back —
    which is exactly what happened on 2026-08-18. Pass keep_users=False for a
    genuinely empty database, as the test suite does.
    """
    wait_for_mysql()

    conn = connect(database=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()

    conn = connect()
    try:
        with conn.cursor() as cursor:
            saved = _read_users(cursor) if keep_users else []

            for statement in _statements(SCHEMA_PATH.read_text()):
                cursor.execute(statement)

            restored = _restore_users(cursor, saved)
        conn.commit()
    finally:
        conn.close()

    # schema.sql is the current state of the schema, so everything the migrations
    # would do is already here. Recording them keeps `migrate` a no-op on a fresh
    # database instead of replaying changes against a schema that has them.
    from db.migrate import stamp_all

    stamped = stamp_all()

    print(f"Database initialized: {Config.MYSQL_DATABASE}")
    if saved:
        print(f"Accounts preserved: {restored} of {len(saved)}")
    if stamped:
        print(f"Migrations stamped as applied: {stamped}")
