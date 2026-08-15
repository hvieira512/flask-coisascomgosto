"""Data access for the collections table.

A collection is a themed grouping such as "Barra da Saia". It owns the colour
sets that its products draw their variants from.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class CollectionRepository:
    """All SQL touching the collections table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        """Return a page of collections, optionally fuzzy-matched on name."""
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT id, name, description FROM collections {where} "
            "ORDER BY id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        """Count collections matching the same filter as `list`."""
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM collections {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, collection_id: int) -> Optional[dict]:
        """Return a collection by ID, or None if not found."""
        self._cursor.execute(
            "SELECT id, name, description FROM collections WHERE id = %s",
            (collection_id,),
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, collection_id: int) -> bool:
        """Check whether a collection exists by ID."""
        self._cursor.execute(
            "SELECT 1 FROM collections WHERE id = %s", (collection_id,)
        )
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one collection."""
        if exclude_id is None:
            self._cursor.execute("SELECT 1 FROM collections WHERE name = %s", (name,))
        else:
            self._cursor.execute(
                "SELECT 1 FROM collections WHERE name = %s AND id <> %s",
                (name, exclude_id),
            )
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(self, *, name: str, description: Optional[str] = None) -> int:
        """Insert a collection and return its new ID."""
        self._cursor.execute(
            "INSERT INTO collections (name, description) VALUES (%s, %s)",
            (name, description),
        )
        return self._cursor.lastrowid

    def update(
        self, collection_id: int, *, name: str, description: Optional[str] = None
    ) -> None:
        """Overwrite a collection's fields."""
        self._cursor.execute(
            "UPDATE collections SET name = %s, description = %s WHERE id = %s",
            (name, description, collection_id),
        )

    def delete(self, collection_id: int) -> None:
        """Delete a collection, detaching its colour sets and products.

        Replaces the old ON DELETE SET NULL: both keep existing, unowned.
        """
        self._cursor.execute(
            "UPDATE color_sets SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute(
            "UPDATE products SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute("DELETE FROM collections WHERE id = %s", (collection_id,))

    # ----------------
    # Internals
    # ----------------

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s", [f"%{term}%"]
