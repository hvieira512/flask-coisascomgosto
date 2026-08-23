"""Data access for the materials table."""

from __future__ import annotations

from repositories.base import NameTableRepository


class MaterialRepository(NameTableRepository):
    TABLE = "materials"

    def create(self, name: str) -> int:
        self._cursor.execute("INSERT INTO materials (name) VALUES (%s)", (name,))
        return self._cursor.lastrowid

    def update(self, material_id: int, name: str) -> None:
        self._cursor.execute(
            "UPDATE materials SET name = %s WHERE id = %s", (name, material_id)
        )

    def delete(self, material_id: int) -> None:
        """Delete a material, leaving the pieces made of it in place.

        Material is descriptive, not structural — a piece does not stop existing
        because the owners tidied the material list, so it loses this material and
        keeps any others. The schema says the same thing (ON DELETE CASCADE on the
        join); doing it here keeps the behaviour readable where it is decided
        rather than only in the constraint.
        """
        self._cursor.execute(
            "DELETE FROM product_materials WHERE material_id = %s", (material_id,)
        )
        self._cursor.execute("DELETE FROM materials WHERE id = %s", (material_id,))
