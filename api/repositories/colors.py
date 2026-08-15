"""Data access for the colors table."""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class ColorRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT id, name, hex FROM colors {where} ORDER BY id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM colors {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, color_id: int) -> Optional[dict]:
        self._cursor.execute(
            "SELECT id, name, hex FROM colors WHERE id = %s", (color_id,)
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, color_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM colors WHERE id = %s", (color_id,))
        return self._cursor.fetchone() is not None

    def missing_ids(self, color_ids: list[int]) -> list[int]:
        """Return the subset of `color_ids` that do not exist.

        Used to reject a colour set referencing unknown colours in one query
        rather than looping per ID.
        """
        if not color_ids:
            return []
        placeholders = ", ".join(["%s"] * len(color_ids))
        self._cursor.execute(
            f"SELECT id FROM colors WHERE id IN ({placeholders})", list(color_ids)
        )
        found = {row["id"] for row in self._cursor.fetchall()}
        return [cid for cid in color_ids if cid not in found]

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one colour."""
        if exclude_id is None:
            self._cursor.execute("SELECT 1 FROM colors WHERE name = %s", (name,))
        else:
            self._cursor.execute(
                "SELECT 1 FROM colors WHERE name = %s AND id <> %s", (name, exclude_id)
            )
        return self._cursor.fetchone() is not None

    def create(self, *, name: str, hex: Optional[str] = None) -> int:
        self._cursor.execute(
            "INSERT INTO colors (name, hex) VALUES (%s, %s)", (name, hex)
        )
        return self._cursor.lastrowid

    def update(self, color_id: int, *, name: str, hex: Optional[str] = None) -> None:
        self._cursor.execute(
            "UPDATE colors SET name = %s, hex = %s WHERE id = %s", (name, hex, color_id)
        )

    def delete(self, color_id: int) -> None:
        """Delete a colour, removing it from any colour set that used it.

        With no foreign keys, the join rows are cleared here.
        """
        self._cursor.execute(
            "DELETE FROM color_set_colors WHERE color_id = %s", (color_id,)
        )
        self._cursor.execute("DELETE FROM colors WHERE id = %s", (color_id,))

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s", [f"%{term}%"]
