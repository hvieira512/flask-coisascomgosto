"""Data access for product types and their sub-types.

A type says what the object *is*: a hairbrush, a picture frame, a wooden box.
Sub-types capture how that object is finished or used. A "Coracao" — a wooden
plaque cut in the shape of the regional Viana heart — may be sold with a string
so it can be hung, or as a base for mini figures displayed on top; those are two
sub-types of one type.

Types nest exactly one level. `NestingTooDeepError` is raised rather than
silently allowing a sub-type of a sub-type.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor


class NestingTooDeepError(ValueError):
    """Raised when a sub-type would be parented to another sub-type."""


class ProductTypeRepository:
    """All SQL touching the product_types table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list(
        self,
        *,
        search: Optional[str] = None,
        parent_id: Optional[int] = None,
        roots_only: bool = False,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Return a page of types, each with its sub-types resolved.

        `roots_only` restricts to top-level types; `parent_id` restricts to the
        sub-types of one type. They are mutually exclusive at the route layer.
        """
        where, params = self._filter(search, parent_id, roots_only)
        self._cursor.execute(
            f"SELECT id, name, description, parent_id, icon FROM product_types {where} "
            "ORDER BY id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        types = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_children(types)
        return types

    def count(
        self,
        *,
        search: Optional[str] = None,
        parent_id: Optional[int] = None,
        roots_only: bool = False,
    ) -> int:
        """Count types matching the same filter as `list`."""
        where, params = self._filter(search, parent_id, roots_only)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM product_types {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, type_id: int) -> Optional[dict]:
        """Return a type with its sub-types, or None if not found."""
        self._cursor.execute(
            "SELECT id, name, description, parent_id, icon FROM product_types WHERE id = %s",
            (type_id,),
        )
        row = self._cursor.fetchone()
        if not row:
            return None

        result = self._to_dict(row)
        self._attach_children([result])
        return result

    def exists(self, type_id: int) -> bool:
        """Check whether a type exists by ID."""
        self._cursor.execute("SELECT 1 FROM product_types WHERE id = %s", (type_id,))
        return self._cursor.fetchone() is not None

    def is_sub_type(self, type_id: int) -> bool:
        """Check whether a type already has a parent."""
        self._cursor.execute(
            "SELECT parent_id FROM product_types WHERE id = %s", (type_id,)
        )
        row = self._cursor.fetchone()
        return bool(row and row["parent_id"] is not None)

    def name_exists(
        self, name: str, *, parent_id: Optional[int], exclude_id: Optional[int] = None
    ) -> bool:
        """Check whether `name` is taken among siblings.

        Names only need to be unique within one parent, so two different types
        may each have a "Small" sub-type. `IS` is used because SQL equality
        never matches NULL, which is how top-level types are stored.
        """
        sql = "SELECT 1 FROM product_types WHERE name = %s AND parent_id <=> %s"
        params: list = [name, parent_id]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        self._cursor.execute(sql, params)
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(
        self,
        *,
        name: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> int:
        """Insert a type or sub-type and return its new ID.

        Raises NestingTooDeepError if `parent_id` is itself a sub-type.
        """
        if parent_id is not None and self.is_sub_type(parent_id):
            raise NestingTooDeepError(
                f"Product type #{parent_id} is already a sub-type; "
                "types nest only one level deep."
            )

        self._cursor.execute(
            "INSERT INTO product_types (name, parent_id, description, icon) "
            "VALUES (%s, %s, %s, %s)",
            (name, parent_id, description, icon),
        )
        return self._cursor.lastrowid

    def update(
        self,
        type_id: int,
        *,
        name: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> None:
        """Overwrite a type's fields, including where it sits in the hierarchy.

        Raises NestingTooDeepError if the move would create a second level of
        nesting, or if a type would become its own parent.
        """
        if parent_id is not None:
            if parent_id == type_id:
                raise NestingTooDeepError("A product type cannot be its own parent.")
            if self.is_sub_type(parent_id):
                raise NestingTooDeepError(
                    f"Product type #{parent_id} is already a sub-type; "
                    "types nest only one level deep."
                )
            if self.has_children(type_id):
                raise NestingTooDeepError(
                    f"Product type #{type_id} has sub-types of its own and "
                    "cannot become a sub-type."
                )

        self._cursor.execute(
            "UPDATE product_types SET name = %s, parent_id = %s, description = %s, "
            "icon = %s WHERE id = %s",
            (name, parent_id, description, icon, type_id),
        )

    def has_children(self, type_id: int) -> bool:
        """Check whether a type has any sub-types."""
        self._cursor.execute(
            "SELECT 1 FROM product_types WHERE parent_id = %s", (type_id,)
        )
        return self._cursor.fetchone() is not None

    def delete(self, type_id: int) -> None:
        """Delete a type and its sub-types, clearing the type on products.

        Products of the deleted types survive with `type_id` cleared, which is
        what the old ON DELETE SET NULL did.
        """
        self._cursor.execute(
            "SELECT id FROM product_types WHERE parent_id = %s", (type_id,)
        )
        ids = [row["id"] for row in self._cursor.fetchall()] + [type_id]

        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            f"UPDATE products SET type_id = NULL WHERE type_id IN ({placeholders})",
            ids,
        )
        self._cursor.execute(
            f"DELETE FROM product_types WHERE id IN ({placeholders})", ids
        )

    # ----------------
    # Internals
    # ----------------

    def _attach_children(self, types: list[dict]) -> None:
        """Populate `sub_types` for a whole page in one query."""
        if not types:
            return

        ids = [t["id"] for t in types]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT id, name, description, parent_id, icon FROM product_types "
            f"WHERE parent_id IN ({placeholders}) ORDER BY parent_id, id",
            ids,
        )

        by_parent: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_parent[row["parent_id"]].append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "icon": row["icon"],
                }
            )

        for t in types:
            t["sub_types"] = by_parent[t["id"]]

    @staticmethod
    def _filter(
        search: Optional[str], parent_id: Optional[int], roots_only: bool
    ) -> Tuple[str, list]:
        clauses, params = [], []

        if term := (search or "").strip():
            clauses.append("name LIKE %s")
            params.append(f"%{term}%")

        if parent_id is not None:
            clauses.append("parent_id = %s")
            params.append(parent_id)
        elif roots_only:
            clauses.append("parent_id IS NULL")

        return ("WHERE " + " AND ".join(clauses) if clauses else ""), params

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "parent_id": row["parent_id"],
            "icon": row["icon"],
            "sub_types": [],
        }
