from datetime import datetime
import re
import sqlite3

from flask import Flask

DB_PATH = "db/coisascomgosto.db"


def init_db():
    with open("db/schema.sql") as f:
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(f.read())
        conn.close()
        print("Database initialized.")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all(query, params=()):
    with get_db_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()


def fetch_one(query, params=()):
    with get_db_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchone()


def execute(query, params=()):
    with get_db_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def execute_many(query, params=()):
    with get_db_connection() as conn:
        cur = conn.executemany(query, params)
        conn.commit()
        return cur.lastrowid


def build_update_query(
    table: str, data: dict, where_clause: str, where_values: tuple
) -> tuple[str, tuple]:
    set_clause = ", ".join([f"{key} = ?" for key in data])
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    values = tuple(data.values()) + where_values
    return query, values


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
