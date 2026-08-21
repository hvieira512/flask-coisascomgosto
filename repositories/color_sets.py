"""Data access for colour sets.

A colour set is a named combination of two or more colours, named once and
shared: the same two colours are the same combination whichever collection shows
them. So it carries no owning collection — the collections it appears in are a
join, and a set may be in several or in none.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor

from repositories.base import one_row

_SELECT = """
    SELECT cs.id AS id, cs.name AS name
    FROM color_sets cs
"""

# Filtering by collection is a join rather than a column, so the FROM clause
# changes with the filter rather than the WHERE alone.
_JOIN_COLLECTION = (
    " JOIN collection_color_sets ccs ON ccs.color_set_id = cs.id"
)


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
        """Return a page of colour sets, each with its colours and collections."""
        join, where, params = self._filter(search, collection_id)
        self._cursor.execute(
            f"{_SELECT} {join} {where} ORDER BY cs.id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_colors(rows)
        self._attach_collections(rows)
        return rows

    def count(
        self, *, search: Optional[str] = None, collection_id: Optional[int] = None
    ) -> int:
        join, where, params = self._filter(search, collection_id)
        self._cursor.execute(
            f"SELECT COUNT(*) AS total FROM color_sets cs {join} {where}", params
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
        self._attach_collections([result])
        return result

    def exists(self, color_set_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM color_sets WHERE id = %s", (color_set_id,))
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken.

        Across the whole table, not within a collection: one combination is named
        once and shared, so a second "Preto e Branco" is the same set spelled
        twice rather than another collection's own.
        """
        sql = "SELECT 1 FROM color_sets WHERE name = %s"
        params: list = [name]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        self._cursor.execute(sql, params)
        return self._cursor.fetchone() is not None

    def set_for_collection(self, collection_id: int, color_set_ids: list[int]) -> None:
        """Make exactly `color_set_ids` the sets this collection gathers.

        A link rather than a move: a set listed here keeps whatever other
        collections it is in, and one dropped from this collection keeps them too.
        """
        self._cursor.execute(
            "DELETE FROM collection_color_sets WHERE collection_id = %s",
            (collection_id,),
        )
        for color_set_id in dict.fromkeys(color_set_ids):
            self._cursor.execute(
                "INSERT INTO collection_color_sets (collection_id, color_set_id) "
                "VALUES (%s, %s)",
                (collection_id, color_set_id),
            )

    def set_collections(self, color_set_id: int, collection_ids: list[int]) -> None:
        """The same from the set's side: exactly these collections, no others."""
        self._cursor.execute(
            "DELETE FROM collection_color_sets WHERE color_set_id = %s",
            (color_set_id,),
        )
        for collection_id in dict.fromkeys(collection_ids):
            self._cursor.execute(
                "INSERT INTO collection_color_sets (collection_id, color_set_id) "
                "VALUES (%s, %s)",
                (collection_id, color_set_id),
            )

    def create(
        self,
        *,
        name: str,
        color_ids: list[int],
        collection_ids: Optional[list[int]] = None,
    ) -> int:
        """Insert a colour set with its colours and return the new ID."""
        self._cursor.execute("INSERT INTO color_sets (name) VALUES (%s)", (name,))
        color_set_id = self._cursor.lastrowid
        self._replace_colors(color_set_id, color_ids)
        self.set_collections(color_set_id, collection_ids or [])
        return color_set_id

    def update(
        self,
        color_set_id: int,
        *,
        name: str,
        color_ids: list[int],
        collection_ids: Optional[list[int]] = None,
    ) -> None:
        """Overwrite a colour set's name, its colours and its collections."""
        self._cursor.execute(
            "UPDATE color_sets SET name = %s WHERE id = %s", (name, color_set_id)
        )
        self._replace_colors(color_set_id, color_ids)
        self.set_collections(color_set_id, collection_ids or [])

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
        self._cursor.execute(
            "DELETE FROM collection_color_sets WHERE color_set_id = %s", (color_set_id,)
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

    def _attach_collections(self, sets: list[dict]) -> None:
        """Populate `collections` on each set, one query for the whole page."""
        if not sets:
            return

        ids = [s["id"] for s in sets]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT ccs.color_set_id, col.id, col.name "
            "FROM collection_color_sets ccs "
            "JOIN collections col ON col.id = ccs.collection_id "
            f"WHERE ccs.color_set_id IN ({placeholders}) "
            "ORDER BY ccs.color_set_id, col.name",
            ids,
        )

        by_set: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_set[row["color_set_id"]].append({"id": row["id"], "name": row["name"]})

        for s in sets:
            s["collections"] = by_set[s["id"]]

    @staticmethod
    def _filter(
        search: Optional[str], collection_id: Optional[int]
    ) -> Tuple[str, str, list]:
        """(join, where, params). Narrowing to a collection is a join now, so the
        filter decides both halves."""
        join, clauses, params = "", [], []

        if term := (search or "").strip():
            clauses.append("cs.name LIKE %s")
            params.append(f"%{term}%")

        if collection_id is not None:
            join = _JOIN_COLLECTION
            clauses.append("ccs.collection_id = %s")
            params.append(collection_id)

        return join, ("WHERE " + " AND ".join(clauses) if clauses else ""), params

    @staticmethod
    def _to_dict(row) -> dict:
        return {"id": row["id"], "name": row["name"], "colors": [], "collections": []}
