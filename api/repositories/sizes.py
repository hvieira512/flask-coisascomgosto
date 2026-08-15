"""Data access for the sizes table.

Sizes are a small controlled vocabulary (S / M / L, seeded by the schema).
A product may name one of them as its default size and/or list the sizes it is
actually available in.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class SizeRepository:
    """All SQL touching the sizes table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        """Return a page of sizes ordered by display position."""
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT id, name, position FROM sizes {where} "
            "ORDER BY position, id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        """Count sizes matching the same filter as `list`."""
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM sizes {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, size_id: int) -> Optional[dict]:
        """Return a size by ID, or None if not found."""
        self._cursor.execute(
            "SELECT id, name, position FROM sizes WHERE id = %s", (size_id,)
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, size_id: int) -> bool:
        """Check whether a size exists by ID."""
        self._cursor.execute("SELECT 1 FROM sizes WHERE id = %s", (size_id,))
        return self._cursor.fetchone() is not None

    def missing_ids(self, size_ids: list[int]) -> list[int]:
        """Return the subset of `size_ids` that do not exist."""
        if not size_ids:
            return []
        placeholders = ", ".join(["%s"] * len(size_ids))
        self._cursor.execute(
            f"SELECT id FROM sizes WHERE id IN ({placeholders})", list(size_ids)
        )
        found = {row["id"] for row in self._cursor.fetchall()}
        return [sid for sid in size_ids if sid not in found]

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one size."""
        if exclude_id is None:
            self._cursor.execute("SELECT 1 FROM sizes WHERE name = %s", (name,))
        else:
            self._cursor.execute(
                "SELECT 1 FROM sizes WHERE name = %s AND id <> %s", (name, exclude_id)
            )
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(self, *, name: str, position: int = 0) -> int:
        """Insert a size and return its new ID."""
        self._cursor.execute(
            "INSERT INTO sizes (name, position) VALUES (%s, %s)", (name, position)
        )
        return self._cursor.lastrowid

    def update(self, size_id: int, *, name: str, position: int = 0) -> None:
        """Overwrite a size's fields."""
        self._cursor.execute(
            "UPDATE sizes SET name = %s, position = %s WHERE id = %s",
            (name, position, size_id),
        )

    def delete(self, size_id: int) -> None:
        """Delete a size, detaching it from every product that referenced it.

        Products listing the size lose it, and any product using it as its
        default size falls back to having no default.
        """
        self._cursor.execute(
            "DELETE FROM product_sizes WHERE size_id = %s", (size_id,)
        )
        self._cursor.execute(
            "UPDATE products SET default_size_id = NULL WHERE default_size_id = %s",
            (size_id,),
        )
        self._cursor.execute("DELETE FROM sizes WHERE id = %s", (size_id,))

    # ----------------
    # Internals
    # ----------------

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s", [f"%{term}%"]
