"""MySQL connection handling and schema initialisation.

Connection settings come from config.database_config().
"""

import re
import time
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

from config import database_config, database_name

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"


def connect(*, database: bool = True):
    return pymysql.connect(cursorclass=DictCursor, **database_config(database=database))


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

    database = database_name()
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
