"""Data access for product images.

Every photograph belongs to a product *and* to one of that product's variants,
so it is shown when the customer picks that colour. There is no product-level
photograph: a piece looks different in each colourway, so a photo standing for
the piece as a whole could only ever be one colour's photo doing double duty —
which is what it was, and it decided which tile the catalogue showed.

Removing one marks `deleted_at` and leaves the file alone, so every read here
carries `deleted_at IS NULL`. That is the whole of the mechanism: the owners'
only copy of a photograph may be the one they uploaded from a phone, so removing
it has to be an UPDATE rather than an unlink. uploads.sweep() is the only thing
that deletes either, and only after a grace period.
"""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

_COLUMNS = "id, product_id, variant_id, url, alt, position"

# On every read. A removed photograph still has a row — that is what makes
# removing one reversible — and nothing outside the sweep should ever see it.
_LIVE = "deleted_at IS NULL"


class ProductImageRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list_for_product(
        self, product_id: int, *, variant_id: Optional[int] = None
    ) -> list[dict]:
        """Return a product's images, ordered by display position.

        With no `variant_id`, every photograph of the piece across all its
        colours. Pass a variant to narrow to one colour.
        """
        if variant_id is None:
            self._cursor.execute(
                f"SELECT {_COLUMNS} FROM product_images WHERE product_id = %s "
                f"AND {_LIVE} ORDER BY position, id",
                (product_id,),
            )
        else:
            self._cursor.execute(
                f"SELECT {_COLUMNS} FROM product_images "
                f"WHERE product_id = %s AND variant_id = %s AND {_LIVE} "
                "ORDER BY position, id",
                (product_id, variant_id),
            )
        return [dict(row) for row in self._cursor.fetchall()]

    def get(self, image_id: int) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images WHERE id = %s AND {_LIVE}",
            (image_id,),
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def belongs_to(self, image_id: int, product_id: int) -> bool:
        """Check that an image belongs to the product named in the URL."""
        self._cursor.execute(
            f"SELECT 1 FROM product_images WHERE id = %s AND product_id = %s "
            f"AND {_LIVE}",
            (image_id, product_id),
        )
        return self._cursor.fetchone() is not None

    def create(
        self,
        *,
        product_id: int,
        url: str,
        variant_id: int,
        alt: Optional[str] = None,
        position: int = 0,
    ) -> int:
        """Insert a photograph. `variant_id` is required — the column is NOT NULL,
        so a caller with no colour in mind has nothing to insert."""
        self._cursor.execute(
            "INSERT INTO product_images (product_id, variant_id, url, alt, position) "
            "VALUES (%s, %s, %s, %s, %s)",
            (product_id, variant_id, url, alt, position),
        )
        return self._cursor.lastrowid

    def update(
        self,
        image_id: int,
        *,
        url: str,
        variant_id: int,
        alt: Optional[str] = None,
        position: int = 0,
    ) -> None:
        self._cursor.execute(
            "UPDATE product_images SET url = %s, alt = %s, variant_id = %s, "
            "position = %s WHERE id = %s",
            (url, alt, variant_id, position, image_id),
        )

    def delete(self, image_id: int) -> None:
        """Mark it removed. The row and the file both stay.

        NOW() rather than a value from the caller, so the mark cannot be back-dated
        past the sweep's grace period by accident.
        """
        self._cursor.execute(
            f"UPDATE product_images SET deleted_at = NOW() "
            f"WHERE id = %s AND {_LIVE}",
            (image_id,),
        )

    def restore(self, image_id: int) -> None:
        """Put a removed photograph back. There is no button for this yet — it is
        the reason the row is kept, and one UPDATE is the whole recovery."""
        self._cursor.execute(
            "UPDATE product_images SET deleted_at = NULL WHERE id = %s", (image_id,)
        )

    # ----------------
    # Bulk helpers used when composing product responses
    # ----------------

    def by_variant(self, variant_ids: list[int]) -> dict[int, list[dict]]:
        """Return images for many variants in one query."""
        if not variant_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(variant_ids))
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images "
            f"WHERE variant_id IN ({placeholders}) AND {_LIVE} "
            "ORDER BY variant_id, position, id",
            list(variant_ids),
        )

        grouped: dict[int, list[dict]] = {vid: [] for vid in variant_ids}
        for row in self._cursor.fetchall():
            grouped[row["variant_id"]].append(dict(row))
        return grouped

    # ----------------
    # For the sweep, which is the only thing that deletes anything
    # ----------------

    def referenced_urls(self) -> set[str]:
        """Every URL any row points at, removed ones included.

        A removed photograph is restorable, so its file is still in use as far as
        the sweep is concerned — until the row itself is purged.
        """
        self._cursor.execute("SELECT url FROM product_images")
        return {row["url"] for row in self._cursor.fetchall()}

    def purge_deleted(self, *, older_than_days: int) -> int:
        """Drop the rows marked removed longer ago than that. Returns how many.

        The boundary is inclusive: DATETIME has second granularity, so with
        `older_than_days=0` — an operator saying "purge everything marked" — a
        strict comparison misses a row marked in the current second.
        """
        self._cursor.execute(
            "DELETE FROM product_images "
            "WHERE deleted_at IS NOT NULL AND deleted_at <= NOW() - INTERVAL %s DAY",
            (older_than_days,),
        )
        return self._cursor.rowcount
