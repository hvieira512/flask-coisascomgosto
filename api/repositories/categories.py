"""Data access for the categories table."""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class CategoryRepository:
    """All SQL touching the categories table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        """Return a page of categories, optionally fuzzy-matched on name."""
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT id, name FROM categories {where} ORDER BY id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        """Count categories matching the same filter as `list`."""
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM categories {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, category_id: int) -> Optional[dict]:
        """Return a category by ID, or None if not found."""
        self._cursor.execute(
            "SELECT id, name FROM categories WHERE id = %s", (category_id,)
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, category_id: int) -> bool:
        """Check whether a category exists by ID."""
        self._cursor.execute("SELECT 1 FROM categories WHERE id = %s", (category_id,))
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one category."""
        if exclude_id is None:
            self._cursor.execute("SELECT 1 FROM categories WHERE name = %s", (name,))
        else:
            self._cursor.execute(
                "SELECT 1 FROM categories WHERE name = %s AND id <> %s",
                (name, exclude_id),
            )
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(self, name: str) -> int:
        """Insert a category and return its new ID."""
        self._cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        return self._cursor.lastrowid

    def update(self, category_id: int, name: str) -> None:
        """Rename a category."""
        self._cursor.execute(
            "UPDATE categories SET name = %s WHERE id = %s", (name, category_id)
        )

    def delete(self, category_id: int) -> None:
        """Delete a category and every product filed under it.

        With no foreign keys in the schema this cascade is performed here.
        Products are deleted through ProductRepository so their own images,
        sizes and variants go with them.
        """
        from api.repositories.products import ProductRepository

        self._cursor.execute(
            "SELECT id FROM products WHERE category_id = %s", (category_id,)
        )
        product_ids = [row["id"] for row in self._cursor.fetchall()]

        products = ProductRepository(self._cursor)
        for product_id in product_ids:
            products.delete(product_id)

        self._cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))

    # ----------------
    # Internals
    # ----------------

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s", [f"%{term}%"]
