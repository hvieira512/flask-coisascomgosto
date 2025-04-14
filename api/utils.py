import sqlite3

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
