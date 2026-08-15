"""MySQL connection handling and schema initialisation."""

import os
import re
import time
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

# Also loaded in config.py: the test bootstrap and `flask init-db` reach this
# module without importing config. The call is idempotent.
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
    """`database=False` connects before the schema exists."""
    config = {
        "host": os.environ.get("MYSQL_HOST", DEFAULTS["host"]),
        "port": int(os.environ.get("MYSQL_PORT", DEFAULTS["port"])),
        "user": os.environ.get("MYSQL_USER", DEFAULTS["user"]),
        "password": os.environ.get("MYSQL_PASSWORD", DEFAULTS["password"]),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }
    if database:
        config["database"] = os.environ.get("MYSQL_DATABASE", DEFAULTS["database"])
    return config


def connect(*, database: bool = True):
    return pymysql.connect(**get_db_config(database=database))


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


def _statements(schema: str):
    # Line comments are stripped first: a semicolon inside one would otherwise
    # cut a statement in half.
    without_comments = re.sub(r"--[^\n]*", "", schema)
    return [s.strip() for s in without_comments.split(";") if s.strip()]


def wait_for_mysql(timeout: int = 60) -> None:
    """Block until the server accepts connections.

    The compose healthcheck only covers `docker compose up`; init-db and the
    test runner start outside that ordering.
    """
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


def init_db() -> None:
    """(Re)create the database and every table, dropping what is there."""
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
