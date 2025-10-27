from sqlite3 import Cursor
from typing import Tuple


def build_category_filters(args: dict) -> Tuple[str, list]:
    where_clauses, params = [], []

    if search := (args.get("q") or "").strip():
        where_clauses.append("name LIKE ?")
        params.append(f"%{search}%")

    return (f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""), params


def fetch_category_by_id(cursor: Cursor, category_id: int) -> dict | None:
    """Return a category dict by ID, or None if not found."""
    cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def category_exists_by_name(cursor: Cursor, name: str) -> bool:
    """Check if a category with the given name exists."""
    cursor.execute("SELECT 1 FROM categories WHERE name = ?", (name,))
    return cursor.fetchone() is not None


def category_exists_by_id(cursor: Cursor, id: int) -> bool:
    cursor.execute("SELECT 1 FROM categories WHERE id = ?", (id,))
    return cursor.fetchone() is not None


def category_name_taken(cursor: Cursor, name: str, category_id: int) -> bool:
    """Check if a category name is used by another category (excluding the given ID)."""
    cursor.execute(
        "SELECT 1 FROM categories WHERE id <> ? AND name = ?",
        (category_id, name),
    )
    return cursor.fetchone() is not None
