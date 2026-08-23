"""Data access for the collections table."""

from __future__ import annotations

from typing import Optional

from repositories.base import NameTableRepository


class CollectionRepository(NameTableRepository):
    TABLE = "collections"

    # borrowed_image_url is a photograph of a piece in the collection, so a
    # collection with no cover of its own still shows something instead of a grey
    # box. Reaching the piece goes through the colour set, because that is what a
    # collection gathers: collection -> colour set -> variant -> photograph. The
    # A colour shared with fewer collections wins first: Filigrana and Bordados
    # both reach Branco e Dourado, which nearly every piece has, and ordering by
    # recency alone gave the two of them the same photograph side by side in the
    # rail. Then the most recent piece, so the cover follows what they are making
    # now — though rows predating migration 0011 all carry that migration's date,
    # which makes the order among the first fourteen arbitrary rather than wrong.
    COLUMNS = """
        id, name, description, image_url,
        (SELECT i.url
           FROM collection_color_sets cs
           JOIN product_variants v ON v.color_set_id = cs.color_set_id
           JOIN products p ON p.id = v.product_id
           JOIN product_images i ON i.variant_id = v.id
          WHERE cs.collection_id = collections.id
            AND i.deleted_at IS NULL
          ORDER BY (SELECT COUNT(*)
                      FROM collection_color_sets shared
                     WHERE shared.color_set_id = cs.color_set_id) ASC,
                   p.created_at DESC, i.position, i.id
          LIMIT 1) AS borrowed_image_url
    """

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
        """Delete a collection. Its colour sets and its products survive it.

        The sets are unlinked rather than emptied of anything: a set gathered here
        may be gathered elsewhere too, and it exists in its own right regardless.
        The products lose the collection they named.
        """
        self._cursor.execute(
            "DELETE FROM collection_color_sets WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute(
            "UPDATE products SET collection_id = NULL WHERE collection_id = %s",
            (collection_id,),
        )
        self._cursor.execute("DELETE FROM collections WHERE id = %s", (collection_id,))
