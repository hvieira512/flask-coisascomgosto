"""Data access for the sizes table."""

from __future__ import annotations

from api.repositories.base import NameTableRepository


class SizeRepository(NameTableRepository):
    TABLE = "sizes"
    COLUMNS = "id, name, position"
    # S before M before L, which is what position exists for.
    ORDER_BY = "position, id"

    def create(self, *, name: str, position: int = 0) -> int:
        self._cursor.execute(
            "INSERT INTO sizes (name, position) VALUES (%s, %s)", (name, position)
        )
        return self._cursor.lastrowid

    def update(self, size_id: int, *, name: str, position: int = 0) -> None:
        self._cursor.execute(
            "UPDATE sizes SET name = %s, position = %s WHERE id = %s",
            (name, position, size_id),
        )

    def delete(self, size_id: int) -> None:
        """Delete a size, detaching it from every product that referenced it.

        Products listing the size lose it, and any product using it as its
        default size falls back to having no default.
        """
        self._cursor.execute(
            "DELETE FROM product_sizes WHERE size_id = %s", (size_id,)
        )
        self._cursor.execute(
            "UPDATE products SET default_size_id = NULL WHERE default_size_id = %s",
            (size_id,),
        )
        self._cursor.execute("DELETE FROM sizes WHERE id = %s", (size_id,))
