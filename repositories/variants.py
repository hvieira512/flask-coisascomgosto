"""Data access for product variants.

A variant is one product offered in one colour set. A "Caixa Redonda" sold in
four combinations is a single product with four variants, each pointing at a
colour set — which is shared, so the same set may be behind variants of several
pieces and gathered by several collections.
"""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

# No collections here. A colour set may be gathered by several, and nothing that
# reads a variant has ever used them: the storefront filters by the *product's*
# collection, and the dashboard shows the set's own name. Carrying a list of
# collections through every variant of every product would be a join per page for
# a field nobody reads.
_SELECT = """
    SELECT
        v.id AS id,
        v.product_id AS product_id,
        cs.id AS color_set_id,
        cs.name AS color_set_name
    FROM product_variants v
    JOIN color_sets cs ON v.color_set_id = cs.id
"""


class ProductVariantRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list_for_product(self, product_id: int) -> list[dict]:
        """Return every variant of a product, colours included."""
        self._cursor.execute(
            f"{_SELECT} WHERE v.product_id = %s ORDER BY v.id", (product_id,)
        )
        variants = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_colors(variants)
        self._attach_images(variants)
        return variants

    def get(self, variant_id: int) -> Optional[dict]:
        self._cursor.execute(f"{_SELECT} WHERE v.id = %s", (variant_id,))
        row = self._cursor.fetchone()
        if not row:
            return None

        variant = self._to_dict(row)
        self._attach_colors([variant])
        self._attach_images([variant])
        return variant

    def exists_for_color_set(self, product_id: int, color_set_id: int) -> bool:
        """Check whether a product already has a variant in this colour set."""
        self._cursor.execute(
            "SELECT 1 FROM product_variants WHERE product_id = %s AND color_set_id = %s",
            (product_id, color_set_id),
        )
        return self._cursor.fetchone() is not None

    def belongs_to(self, variant_id: int, product_id: int) -> bool:
        """Check that a variant belongs to the product in the URL.

        Stops `/products/1/variants/99` from touching another product's variant.
        """
        self._cursor.execute(
            "SELECT 1 FROM product_variants WHERE id = %s AND product_id = %s",
            (variant_id, product_id),
        )
        return self._cursor.fetchone() is not None

    def create(self, *, product_id: int, color_set_id: int) -> int:
        """Attach a colour set to a product and return the new variant ID."""
        self._cursor.execute(
            "INSERT INTO product_variants (product_id, color_set_id) VALUES (%s, %s)",
            (product_id, color_set_id),
        )
        return self._cursor.lastrowid

    def delete(self, variant_id: int) -> None:
        """Remove a variant and its photographs' rows. The colour set is untouched.

        The rows go rather than being marked: a soft-deleted photograph of a colour
        that no longer exists is a state nothing could present. The files stay on
        disk until uploads.sweep() collects them, which is what makes this
        recoverable at all — it used to unlink them here.
        """
        self._cursor.execute(
            "DELETE FROM product_images WHERE variant_id = %s", (variant_id,)
        )
        self._cursor.execute(
            "DELETE FROM product_variants WHERE id = %s", (variant_id,)
        )

    def _attach_colors(self, variants: list[dict]) -> None:
        """Fill in each variant's colour-set colours in one query."""
        if not variants:
            return

        by_color_set: dict[int, list] = {}
        for variant in variants:
            by_color_set.setdefault(variant["color_set"]["id"], []).append(variant)

        ids = list(by_color_set)
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT csc.color_set_id, c.id, c.name, c.hex FROM color_set_colors csc "
            "JOIN colors c ON csc.color_id = c.id "
            f"WHERE csc.color_set_id IN ({placeholders}) "
            "ORDER BY csc.color_set_id, csc.position",
            ids,
        )

        for row in self._cursor.fetchall():
            color = {"id": row["id"], "name": row["name"], "hex": row["hex"]}
            for variant in by_color_set[row["color_set_id"]]:
                variant["color_set"]["colors"].append(color)

    def _attach_images(self, variants: list[dict]) -> None:
        """Populate each variant's own photos in one query."""
        if not variants:
            return

        from repositories.images import ProductImageRepository

        by_variant = ProductImageRepository(self._cursor).by_variant(
            [v["id"] for v in variants]
        )
        for variant in variants:
            variant["images"] = by_variant.get(variant["id"], [])

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "id": row["id"],
            "images": [],
            "color_set": {
                "id": row["color_set_id"],
                "name": row["color_set_name"],
                "colors": [],
            },
        }
