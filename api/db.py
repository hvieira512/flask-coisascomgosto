"""MySQL connection handling and schema initialisation."""

import re
import time
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

from config import Config

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


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


def init_db():
    """(Re)create the database and every table, dropping what is there."""
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
            for statement in _statements(SCHEMA_PATH.read_text()):
                cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()

    print(f"Database initialized: {Config.MYSQL_DATABASE}")
