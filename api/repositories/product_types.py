"""Data access for product types.

A type is the family a piece belongs to: a box, a heart, a picture frame, a
Christmas ornament. It is deliberately flat — the shape and the finish live in
the product's own name, so "Caixa" is the type and "Caixa rectangular" and
"Caixa de Joias" are two products of it.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class ProductTypeRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(self, *, search: Optional[str] = None, limit: int, offset: int) -> list[dict]:
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT id, name, description, icon FROM product_types {where} "
            "ORDER BY id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM product_types {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, type_id: int) -> Optional[dict]:
        self._cursor.execute(
            "SELECT id, name, description, icon FROM product_types WHERE id = %s",
            (type_id,),
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, type_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM product_types WHERE id = %s", (type_id,))
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one type."""
        sql = "SELECT 1 FROM product_types WHERE name = %s"
        params: list = [name]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        self._cursor.execute(sql, params)
        return self._cursor.fetchone() is not None

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
            f"  WHERE p.type_id IN ({placeholders})"
            ") ranked WHERE rank_in_type = 1",
            type_ids,
        )
        return {
            row["type_id"]: {"url": row["url"], "alt": row["alt"]}
            for row in self._cursor.fetchall()
        }

    def product_count(self, type_id: int) -> int:
        """How many pieces are filed under this type."""
        self._cursor.execute(
            "SELECT COUNT(*) AS total FROM products WHERE type_id = %s", (type_id,)
        )
        return self._cursor.fetchone()["total"]

    def delete(self, type_id: int) -> None:
        """Delete a type.

        Only safe once nothing references it: type_id is NOT NULL, so there is no
        "unfile the product" state to fall back on. Callers check product_count
        first and refuse rather than destroy pieces — see the 409 in
        routes/product_types.py.
        """
        self._cursor.execute("DELETE FROM product_types WHERE id = %s", (type_id,))

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        if term := (search or "").strip():
            return "WHERE name LIKE %s", [f"%{term}%"]
        return "", []
