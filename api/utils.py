import re
from contextlib import contextmanager
from datetime import datetime
from sqlite3 import Row, connect

from flask import Flask

DB_PATH = "db/coisascomgosto.db"


def init_db():
    with open("db/schema.sql") as f:
        conn = connect(DB_PATH)
        conn.executescript(f.read())
        conn.close()
        print("Database initialized.")


@contextmanager
def get_db_connection():
    conn = connect(DB_PATH)
    conn.row_factory = Row
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def format_datetime(dt):
    """Helper function to format datetime as DD/MM/YYYY HH:MM"""
    return datetime.strftime(dt, "%d/%m/%Y %H:%M") if dt else None


def format_date(dt):
    """Helper function to format datetime as DD/MM/YYYY"""
    return datetime.strftime(dt, "%d/%m/%Y") if dt else None


EMAIL_REGEX = re.compile(
    r"([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Za-z]{2,})+"
)


def is_email_valid(email: str) -> bool:
    """Validate an email address using a regex."""
    return bool(EMAIL_REGEX.fullmatch(email))


def print_routes(prefix: str, app: Flask):
    """Prints the routes with a given endpoint prefix (e.g., 'api' or 'web')"""
    print("-" * 120)
    print(f"{prefix.upper():^120}")
    print("-" * 120)

    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith(f"{prefix}."):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"{methods:8} {rule.rule:50} -> {rule.endpoint}")
