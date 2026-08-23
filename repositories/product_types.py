"""Data access for product types.

A type is the family a piece belongs to: a box, a heart, a picture frame, a
Christmas ornament. It is deliberately flat — the shape and the finish live in
the product's own name, so "Caixa" is the type and "Caixa rectangular" and
"Caixa de Joias" are two products of it.
"""

from __future__ import annotations

from typing import Optional

from repositories.base import NameTableRepository, one_row


class ProductTypeRepository(NameTableRepository):
    """Flat, so it is one of the name tables: count, exists and name_exists come
    from the base unchanged, and it kept its own copies of them only while types
    had a parent_id to filter on. `list` and `get` wrap the base's to add how many
    pieces the type holds and a photograph of one of them, because a type is not
    much use as a name on its own."""

    TABLE = "product_types"
    COLUMNS = "id, name, description, icon"

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        return self._with_pieces(
            super().list(search=search, limit=limit, offset=offset)
        )

    def get(self, row_id: int) -> Optional[dict]:
        row = super().get(row_id)
        return self._with_pieces([row])[0] if row else None

    def _with_pieces(self, types: list[dict]) -> list[dict]:
        """A type reads as the family it is: how many pieces it holds, and one of
        their photographs. Both come from the queries the landing page already
        asks, so the dashboard does not have to fetch every product to count."""
        ids = [t["id"] for t in types]
        counts = self.product_counts(ids)
        covers = self.cover_images(ids)

        for row in types:
            row["pieces"] = counts.get(row["id"], 0)
            row["image"] = covers.get(row["id"])
        return types

    def create(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> int:
        self._cursor.execute(
            "INSERT INTO product_types (name, description, icon) VALUES (%s, %s, %s)",
            (name, description, icon),
        )
        return self._cursor.lastrowid

    def update(
        self,
        type_id: int,
        *,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> None:
        self._cursor.execute(
            "UPDATE product_types SET name = %s, description = %s, icon = %s "
            "WHERE id = %s",
            (name, description, icon, type_id),
        )

    def cover_images(self, type_ids: list[int]) -> dict[int, dict]:
        """One photograph per type, to stand for the whole family on the landing
        page.

        Ranked rather than grouped so the choice is stable across requests: the
        first photograph of the earliest piece wins.
        """
        if not type_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(type_ids))
        self._cursor.execute(
            "SELECT type_id, url, alt FROM ("
            "  SELECT p.type_id, i.url, IFNULL(i.alt, p.name) AS alt,"
            "         ROW_NUMBER() OVER ("
            "           PARTITION BY p.type_id"
            "           ORDER BY i.product_id, i.position, i.id) AS rank_in_type"
            "  FROM product_images i"
            "  JOIN products p ON p.id = i.product_id"
            f"  WHERE p.type_id IN ({placeholders}) AND i.deleted_at IS NULL"
            ") ranked WHERE rank_in_type = 1",
            type_ids,
        )
        return {
            row["type_id"]: {"url": row["url"], "alt": row["alt"]}
            for row in self._cursor.fetchall()
        }

    def product_counts(self, type_ids: list[int]) -> dict[int, int]:
        """How many pieces each type holds, in one query.

        The landing page names the count on every family tile, and asking
        product_count() once per tile is six queries for one number.
        """
        if not type_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(type_ids))
        self._cursor.execute(
            "SELECT type_id, COUNT(*) AS total FROM products "
            f"WHERE type_id IN ({placeholders}) GROUP BY type_id",
            type_ids,
        )
        return {row["type_id"]: row["total"] for row in self._cursor.fetchall()}

    def product_count(self, type_id: int) -> int:
        """How many pieces are filed under this type."""
        self._cursor.execute(
            "SELECT COUNT(*) AS total FROM products WHERE type_id = %s", (type_id,)
        )
        return one_row(self._cursor)["total"]

    def delete(self, type_id: int) -> None:
        """Delete a type.

        Only safe once nothing references it: type_id is NOT NULL, so there is no
        "unfile the product" state to fall back on. Callers check product_count
        first and refuse rather than destroy pieces — see the 409 in
        routes/product_types.py.
        """
        self._cursor.execute("DELETE FROM product_types WHERE id = %s", (type_id,))
