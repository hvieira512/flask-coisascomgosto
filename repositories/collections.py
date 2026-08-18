"""Data access for the collections table."""

from __future__ import annotations

from typing import Optional

from repositories.base import NameTableRepository


class CollectionRepository(NameTableRepository):
    TABLE = "collections"
    COLUMNS = "id, name, description, image_url"

    def create(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> int:
        self._cursor.execute(
            "INSERT INTO collections (name, description, image_url) "
            "VALUES (%s, %s, %s)",
            (name, description, image_url),
        )
        return self._cursor.lastrowid

    def update(
        self,
        collection_id: int,
        *,
        name: str,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> None:
        self._cursor.execute(
            "UPDATE collections SET name = %s, description = %s, image_url = %s "
            "WHERE id = %s",
            (name, description, image_url, collection_id),
        )

    def delete(self, collection_id: int) -> None:
        """Delete a collection, detaching its colour sets and products.

        Replaces the old ON DELETE SET NULL: both keep existing, unowned.
        """
        self._cursor.execute(
            "UPDATE color_sets SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute(
            "UPDATE products SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute("DELETE FROM collections WHERE id = %s", (collection_id,))
