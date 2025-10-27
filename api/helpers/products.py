from sqlite3 import Cursor
from typing import Tuple


def build_product_filters(args: dict) -> Tuple[str, list]:
    where_clauses, params = [], []

    if search := (args.get("q") or "").strip():
        where_clauses.append("name LIKE ?")
        params.append(f"%{search}%")

    return (f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""), params


def fetch_product_by_id(cursor: Cursor, product_id: int) -> dict | None:
    """Return a product dict by ID with its category, or None if not found."""
    cursor.execute(
        """
        SELECT 
            p.id AS id,
            p.name AS name,
            p.description AS description,
            c.id AS category_id,
            c.name AS category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
    """,
        (product_id,),
    )

    row = cursor.fetchone()
    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": {"id": row["category_id"], "name": row["category_name"]},
    }


def product_exists_by_name(cursor: Cursor, name: str) -> bool:
    """Check if a product with the given name name exists."""
    cursor.execute("SELECT 1 FROM products WHERE name = ?", (name,))
    return cursor.fetchone() is not None


def product_name_taken(cursor: Cursor, name: str, product_id: int) -> bool:
    """Check if a product name is used by other another product (excluding the given ID)."""
    cursor.execute(
        "SELECT 1 FROM products WHERE id <> ? AND name = ?", (product_id, name)
    )
    return cursor.fetchone() is not None
