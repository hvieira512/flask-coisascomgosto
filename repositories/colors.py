"""Data access for the colors table."""

from __future__ import annotations

from typing import Optional

from repositories.base import NameTableRepository


class ColorRepository(NameTableRepository):
    TABLE = "colors"
    COLUMNS = "id, name, hex"

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

        The join rows are cleared here as well as by ON DELETE CASCADE, so the
        behaviour is stated where it is decided.
        """
        self._cursor.execute(
            "DELETE FROM color_set_colors WHERE color_id = %s", (color_id,)
        )
        self._cursor.execute("DELETE FROM colors WHERE id = %s", (color_id,))
