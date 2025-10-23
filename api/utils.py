from datetime import datetime
import re
from sqlite3 import Connection, Cursor, connect, Row

from flask import Flask

DB_PATH = "db/coisascomgosto.db"


def init_db():
    with open("db/schema.sql") as f:
        conn = connect(DB_PATH)
        conn.executescript(f.read())
        conn.close()
        print("Database initialized.")


def get_db_connection() -> tuple[Connection, Cursor]:
    conn = connect(DB_PATH)
    conn.row_factory = Row
    cursor = conn.cursor()
    return conn, cursor


def format_datetime(dt):
    """Helper function to format datetime as DD/MM/YYYY HH:MM"""
    if not dt:
        return None

    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return dt

    return dt.strftime("%d/%m/%Y %H:%M")


def format_date(dt):
    return datetime.strftime(dt, "%d/%m/%Y") if dt else None


def is_email_valid(email):
    """Function that validates an email"""
    regex = re.compile(
        r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"
    )
    if re.fullmatch(regex, email):
        return True
    else:
        return False


def print_routes(prefix: str, app: Flask):
    """Prints the routes with a given endpoint prefix (e.g., 'api' or 'web')"""
    print("-" * 120)
    print(f"{prefix.upper():^120}")
    print("-" * 120)

    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith(f"{prefix}."):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"{methods:8} {rule.rule:50} -> {rule.endpoint}")
