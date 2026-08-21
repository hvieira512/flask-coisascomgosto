"""Data access for colour sets."""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor

from repositories.base import one_row

_SELECT = """
    SELECT
        cs.id AS id,
        cs.name AS name,
        col.id AS collection_id,
        col.name AS collection_name
    FROM color_sets cs
    LEFT JOIN collections col ON cs.collection_id = col.id
"""


class ColorSetRepository:
    """All SQL touching color_sets and its colour join table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(
        self,
        *,
        search: Optional[str] = None,
        collection_id: Optional[int] = None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Return a page of colour sets, each with its colours resolved."""
        where, params = self._filter(search, collection_id)
        self._cursor.execute(
            f"{_SELECT} {where} ORDER BY cs.id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_colors(rows)
        return rows

    def count(
        self, *, search: Optional[str] = None, collection_id: Optional[int] = None
    ) -> int:
        where, params = self._filter(search, collection_id)
        self._cursor.execute(
            "SELECT COUNT(*) AS total FROM color_sets cs "
            "LEFT JOIN collections col ON cs.collection_id = col.id "
            f"{where}",
            params,
        )
        return one_row(self._cursor)["total"]

    def get(self, color_set_id: int) -> Optional[dict]:
        """Return a colour set with its colours, or None if not found."""
        self._cursor.execute(f"{_SELECT} WHERE cs.id = %s", (color_set_id,))
        row = self._cursor.fetchone()
        if not row:
            return None

        result = self._to_dict(row)
        self._attach_colors([result])
        return result

    def exists(self, color_set_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM color_sets WHERE id = %s", (color_set_id,))
        return self._cursor.fetchone() is not None

    def name_exists(
        self,
        name: str,
        *,
        collection_id: Optional[int],
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check whether `name` is taken within the same collection.

        Two collections may each have a "White and Green"; one collection may
        not have it twice. `collection_id=None` scopes to unowned sets, and is
        compared with `IS` because SQL equality never matches NULL.
        """
        sql = "SELECT 1 FROM color_sets WHERE name = %s AND collection_id <=> %s"
        params: list = [name, collection_id]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        self._cursor.execute(sql, params)
        return self._cursor.fetchone() is not None

    def set_collection(self, collection_id: int, color_set_ids: list[int]) -> None:
        """Make exactly `color_set_ids` the sets belonging to this collection.

        A colour set belongs to at most one collection, so this is a move rather than
        a link: a set listed here leaves whichever collection it was in, and one that
        was in this collection and is no longer listed is left belonging to none.
        """
        self._cursor.execute(
            "UPDATE color_sets SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        if not color_set_ids:
            return

        placeholders = ", ".join(["%s"] * len(color_set_ids))
        self._cursor.execute(
            f"UPDATE color_sets SET collection_id = %s WHERE id IN ({placeholders})",
            [collection_id, *color_set_ids],
        )

    def create(
        self, *, name: str, collection_id: Optional[int], color_ids: list[int]
    ) -> int:
        """Insert a colour set with its colours and return the new ID."""
        self._cursor.execute(
            "INSERT INTO color_sets (name, collection_id) VALUES (%s, %s)",
            (name, collection_id),
        )
        color_set_id = self._cursor.lastrowid
        self._replace_colors(color_set_id, color_ids)
        return color_set_id

    def update(
        self,
        color_set_id: int,
        *,
        name: str,
        collection_id: Optional[int],
        color_ids: list[int],
    ) -> None:
        """Overwrite a colour set's fields and its colour membership."""
        self._cursor.execute(
            "UPDATE color_sets SET name = %s, collection_id = %s WHERE id = %s",
            (name, collection_id, color_set_id),
        )
        self._replace_colors(color_set_id, color_ids)

    def delete(self, color_set_id: int) -> None:
        """Delete a colour set, its colour membership and any variant using it.

        Variants go through ProductVariantRepository rather than a bare DELETE, so
        their photographs' rows go the same way they do everywhere else. The files
        stay on disk for uploads.sweep().
        """
        from repositories.variants import ProductVariantRepository

        self._cursor.execute(
            "SELECT id FROM product_variants WHERE color_set_id = %s", (color_set_id,)
        )
        variant_ids = [row["id"] for row in self._cursor.fetchall()]

        variants = ProductVariantRepository(self._cursor)
        for variant_id in variant_ids:
            variants.delete(variant_id)

        self._cursor.execute(
            "DELETE FROM color_set_colors WHERE color_set_id = %s", (color_set_id,)
        )
        self._cursor.execute("DELETE FROM color_sets WHERE id = %s", (color_set_id,))

    def _replace_colors(self, color_set_id: int, color_ids: list[int]) -> None:
        """Reset a set's colours to exactly `color_ids`, preserving order."""
        self._cursor.execute(
            "DELETE FROM color_set_colors WHERE color_set_id = %s", (color_set_id,)
        )
        # dict.fromkeys drops duplicates while keeping the caller's ordering,
        # which the composite primary key would otherwise reject.
        for position, color_id in enumerate(dict.fromkeys(color_ids)):
            self._cursor.execute(
                "INSERT INTO color_set_colors (color_set_id, color_id, position) "
                "VALUES (%s, %s, %s)",
                (color_set_id, color_id, position),
            )

    def _attach_colors(self, sets: list[dict]) -> None:
        """Populate `colors` on each set using one query for the whole page."""
        if not sets:
            return

        ids = [s["id"] for s in sets]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT csc.color_set_id, c.id, c.name, c.hex "
            "FROM color_set_colors csc "
            "JOIN colors c ON csc.color_id = c.id "
            f"WHERE csc.color_set_id IN ({placeholders}) "
            "ORDER BY csc.color_set_id, csc.position",
            ids,
        )

        by_set: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_set[row["color_set_id"]].append(
                {"id": row["id"], "name": row["name"], "hex": row["hex"]}
            )

        for s in sets:
            s["colors"] = by_set[s["id"]]

    @staticmethod
    def _filter(
        search: Optional[str], collection_id: Optional[int]
    ) -> Tuple[str, list]:
        clauses, params = [], []

        if term := (search or "").strip():
            clauses.append("cs.name LIKE %s")
            params.append(f"%{term}%")

        if collection_id is not None:
            clauses.append("cs.collection_id = %s")
            params.append(collection_id)

        return ("WHERE " + " AND ".join(clauses) if clauses else ""), params

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "collection": (
                {"id": row["collection_id"], "name": row["collection_name"]}
                if row["collection_id"] is not None
                else None
            ),
            "colors": [],
        }
