"""Data access for product images.

An image belongs to a product, and optionally to one of that product's variants.
A variant-scoped image is shown when the customer picks that colour set; a
product-scoped image (variant_id NULL) is the fallback used when a variant has
no photos of its own.
"""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

_COLUMNS = "id, product_id, variant_id, url, alt, position"


class ProductImageRepository:
    """All SQL touching the product_images table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list_for_product(
        self, product_id: int, *, variant_id: Optional[int] = None
    ) -> list[dict]:
        """Return a product's images, newest-ordered by display position.

        With no `variant_id`, every image for the product is returned including
        variant-scoped ones. Pass a variant to narrow to that colour set.
        """
        if variant_id is None:
            self._cursor.execute(
                f"SELECT {_COLUMNS} FROM product_images WHERE product_id = %s "
                "ORDER BY position, id",
                (product_id,),
            )
        else:
            self._cursor.execute(
                f"SELECT {_COLUMNS} FROM product_images "
                "WHERE product_id = %s AND variant_id = %s ORDER BY position, id",
                (product_id, variant_id),
            )
        return [dict(row) for row in self._cursor.fetchall()]

    def list_product_level(self, product_id: int) -> list[dict]:
        """Return only the images not tied to a variant."""
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images "
            "WHERE product_id = %s AND variant_id IS NULL ORDER BY position, id",
            (product_id,),
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def get(self, image_id: int) -> Optional[dict]:
        """Return an image by ID, or None if not found."""
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images WHERE id = %s", (image_id,)
        )
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def belongs_to(self, image_id: int, product_id: int) -> bool:
        """Check that an image belongs to the product named in the URL."""
        self._cursor.execute(
            "SELECT 1 FROM product_images WHERE id = %s AND product_id = %s",
            (image_id, product_id),
        )
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(
        self,
        *,
        product_id: int,
        url: str,
        alt: Optional[str] = None,
        variant_id: Optional[int] = None,
        position: int = 0,
    ) -> int:
        """Insert an image and return its new ID."""
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
        alt: Optional[str] = None,
        variant_id: Optional[int] = None,
        position: int = 0,
    ) -> None:
        """Overwrite an image's fields."""
        self._cursor.execute(
            "UPDATE product_images SET url = %s, alt = %s, variant_id = %s, "
            "position = %s WHERE id = %s",
            (url, alt, variant_id, position, image_id),
        )

    def delete(self, image_id: int) -> None:
        """Delete an image."""
        self._cursor.execute("DELETE FROM product_images WHERE id = %s", (image_id,))

    # ----------------
    # Bulk helpers used when composing product responses
    # ----------------

    def by_product(self, product_ids: list[int]) -> dict[int, list[dict]]:
        """Return product-level images for many products in one query."""
        if not product_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(product_ids))
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images "
            f"WHERE product_id IN ({placeholders}) AND variant_id IS NULL "
            "ORDER BY product_id, position, id",
            list(product_ids),
        )

        grouped: dict[int, list[dict]] = {pid: [] for pid in product_ids}
        for row in self._cursor.fetchall():
            grouped[row["product_id"]].append(dict(row))
        return grouped

    def by_variant(self, variant_ids: list[int]) -> dict[int, list[dict]]:
        """Return images for many variants in one query."""
        if not variant_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(variant_ids))
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM product_images "
            f"WHERE variant_id IN ({placeholders}) "
            "ORDER BY variant_id, position, id",
            list(variant_ids),
        )

        grouped: dict[int, list[dict]] = {vid: [] for vid in variant_ids}
        for row in self._cursor.fetchall():
            grouped[row["variant_id"]].append(dict(row))
        return grouped
