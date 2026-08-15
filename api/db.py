"""Database connection and schema management.

The application talks to MySQL 8 through PyMySQL, using raw SQL confined to
api/repositories/. Cursors are DictCursors, so every row arrives as a plain
dict — the repositories can keep returning `dict(row)` unchanged.

Connection settings come from the environment so the same image runs against
the compose service, a test database and a production server:

    MYSQL_HOST      default 127.0.0.1
    MYSQL_PORT      default 3306
    MYSQL_USER      default coisascomgosto
    MYSQL_PASSWORD  default coisascomgosto
    MYSQL_DATABASE  default coisascomgosto

The test suite overrides MYSQL_DATABASE to point at a throwaway schema, which
is why the database name is read per call rather than captured at import.
"""

import os
import re
import time
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

# Loaded here as well as in config.py: the test bootstrap and `flask init-db`
# reach this module without ever importing config. The call is idempotent.
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"

DEFAULTS = {
    "host": "127.0.0.1",
    "port": "3306",
    "user": "coisascomgosto",
    "password": "coisascomgosto",
    "database": "coisascomgosto",
}


def get_db_config(*, database: bool = True) -> dict:
    """Read connection settings from the environment.

    `database=False` omits the schema name, which is how the bootstrap connects
    before the database itself exists.
    """
    config = {
        "host": os.environ.get("MYSQL_HOST", DEFAULTS["host"]),
        "port": int(os.environ.get("MYSQL_PORT", DEFAULTS["port"])),
        "user": os.environ.get("MYSQL_USER", DEFAULTS["user"]),
        "password": os.environ.get("MYSQL_PASSWORD", DEFAULTS["password"]),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        # Without this, PyMySQL leaves the connection in a transaction and
        # readers never see another session's committed writes.
        "autocommit": False,
    }
    if database:
        config["database"] = os.environ.get(
            "MYSQL_DATABASE", DEFAULTS["database"]
        )
    return config


def connect(*, database: bool = True):
    """Open a single connection. Callers are responsible for closing it."""
    return pymysql.connect(**get_db_config(database=database))


class _Connection:
    """Adapts PyMySQL's connection to the (conn, cursor) contract.

    Nothing outside this module needs to know the driver changed: callers still
    write `with get_db_connection() as (conn, cursor)`.
    """

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
    """Yield a (connection, cursor) pair, committing on success.

    The schema declares no foreign keys, so there is nothing for MySQL to
    enforce here: every cascade and orphan cleanup lives in the repository
    layer instead.
    """
    return _Connection()


def _statements(schema: str):
    """Split a schema file into individual statements.

    PyMySQL executes one statement per call, so the script has to be split.
    Line comments are stripped first: a stray semicolon inside one would
    otherwise cut a statement in half.
    """
    without_comments = re.sub(r"--[^\n]*", "", schema)
    return [s.strip() for s in without_comments.split(";") if s.strip()]


def wait_for_mysql(timeout: int = 60) -> None:
    """Block until the server accepts connections.

    The app container starts before MySQL has finished initialising, and a
    compose healthcheck only covers `docker compose up` — this covers every
    other entry point too.
    """
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            connect(database=False).close()
            return
        except pymysql.Error as error:  # not ready yet
            last_error = error
            time.sleep(1)

    raise RuntimeError(f"MySQL not reachable after {timeout}s: {last_error}")


def init_db() -> None:
    """(Re)create the database and schema, dropping any existing tables."""
    wait_for_mysql()

    database = os.environ.get("MYSQL_DATABASE", DEFAULTS["database"])
    conn = connect(database=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()

    conn = connect()
    try:
        with conn.cursor() as cursor:
            for statement in _statements(SCHEMA_PATH.read_text()):
                cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()

    print(f"Database initialized: {database}")
