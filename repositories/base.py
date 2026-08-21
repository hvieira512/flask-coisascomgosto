"""Shared reads for the lookup tables.

materials, collections, colors and sizes are all "an id, a name, and maybe one
more column", and all four listed, counted, fetched and name-checked with the
same four statements. Only their writes genuinely differ — different columns,
and a different set of rows to detach on delete — so those stay in the
subclasses, which set TABLE and COLUMNS and nothing else.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


def one_row(cursor: DictCursor) -> dict:
    """The row from a statement that cannot answer with none.

    `SELECT COUNT(*)` returns a row for an empty table, and LAST_INSERT_ID() for
    a failed insert would have raised — but fetchone() is typed as optional
    because most statements can come back empty, so every count in this package
    was subscripting a value a type checker had to assume might be None.

    Raising rather than defaulting to zero: a count that silently reads 0 when
    the driver returned nothing would hide a broken cursor as an empty catalogue.
    """
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("a statement that always returns one row returned none")
    return row


class NameTableRepository:
    TABLE: str
    COLUMNS: str = "id, name"
    ORDER_BY: str = "id"

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT {self.COLUMNS} FROM {self.TABLE} {where} "
            f"ORDER BY {self.ORDER_BY} LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT COUNT(*) AS total FROM {self.TABLE} {where}", params
        )
        return one_row(self._cursor)["total"]

    def get(self, row_id: int) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {self.COLUMNS} FROM {self.TABLE} WHERE id = %s", (row_id,)
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def exists(self, row_id: int) -> bool:
        self._cursor.execute(f"SELECT 1 FROM {self.TABLE} WHERE id = %s", (row_id,))
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Whether `name` is taken, optionally ignoring one row — which is what
        lets a rename keep its own name."""
        if exclude_id is None:
            self._cursor.execute(
                f"SELECT 1 FROM {self.TABLE} WHERE name = %s", (name,)
            )
        else:
            self._cursor.execute(
                f"SELECT 1 FROM {self.TABLE} WHERE name = %s AND id <> %s",
                (name, exclude_id),
            )
        return self._cursor.fetchone() is not None

    def missing_ids(self, row_ids: list[int]) -> list[int]:
        """The subset of `row_ids` that do not exist, in the order given, so a
        caller can name them all in one error rather than one round trip each."""
        if not row_ids:
            return []

        placeholders = ", ".join(["%s"] * len(row_ids))
        self._cursor.execute(
            f"SELECT id FROM {self.TABLE} WHERE id IN ({placeholders})", list(row_ids)
        )
        found = {row["id"] for row in self._cursor.fetchall()}
        return [row_id for row_id in row_ids if row_id not in found]

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s", [f"%{term}%"]
