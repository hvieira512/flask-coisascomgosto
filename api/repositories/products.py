"""Data access for the products table.

A product always has a category. It may additionally belong to a collection,
declare a default size, list the sizes it is available in, and carry variants —
one per colour set it is offered in.
"""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor

# Every read resolves the category (required) plus the optional collection and
# default size, so callers get one consistent product shape.
_FROM = """
    FROM products p
    JOIN categories c ON p.category_id = c.id
    LEFT JOIN collections col ON p.collection_id = col.id
    LEFT JOIN sizes s ON p.default_size_id = s.id
    LEFT JOIN product_types t ON p.type_id = t.id
    LEFT JOIN product_types tp ON t.parent_id = tp.id
"""

_SELECT = f"""
    SELECT
        p.id AS id,
        p.name AS name,
        p.description AS description,
        c.id AS category_id,
        c.name AS category_name,
        col.id AS collection_id,
        col.name AS collection_name,
        s.id AS default_size_id,
        s.name AS default_size_name,
        s.position AS default_size_position,
        t.id AS type_id,
        t.name AS type_name,
        t.icon AS type_icon,
        tp.id AS type_parent_id,
        tp.name AS type_parent_name,
        tp.icon AS type_parent_icon
    {_FROM}
"""


class ProductRepository:
    """All SQL touching products, product_sizes and product_variants lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def list(
        self,
        *,
        search: Optional[str] = None,
        collection_id: Optional[int] = None,
        category_id: Optional[int] = None,
        type_id: Optional[int] = None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Return a page of products with sizes and variants resolved."""
        where, params = self._filter(search, collection_id, category_id, type_id)
        self._cursor.execute(
            f"{_SELECT} {where} ORDER BY p.id LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        products = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_sizes(products)
        self._attach_variants(products)
        self._attach_images(products)
        return products

    def count(
        self,
        *,
        search: Optional[str] = None,
        collection_id: Optional[int] = None,
        category_id: Optional[int] = None,
        type_id: Optional[int] = None,
    ) -> int:
        """Count products matching the same filter as `list`."""
        where, params = self._filter(search, collection_id, category_id, type_id)
        self._cursor.execute(f"SELECT COUNT(*) AS total {_FROM} {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, product_id: int) -> Optional[dict]:
        """Return a product with its category, collection, sizes and variants."""
        self._cursor.execute(f"{_SELECT} WHERE p.id = %s", (product_id,))
        row = self._cursor.fetchone()
        if not row:
            return None

        product = self._to_dict(row)
        self._attach_sizes([product])
        self._attach_variants([product])
        self._attach_images([product])
        return product

    def exists(self, product_id: int) -> bool:
        """Check whether a product exists by ID."""
        self._cursor.execute("SELECT 1 FROM products WHERE id = %s", (product_id,))
        return self._cursor.fetchone() is not None

    def name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        """Check whether `name` is taken, optionally ignoring one product."""
        if exclude_id is None:
            self._cursor.execute("SELECT 1 FROM products WHERE name = %s", (name,))
        else:
            self._cursor.execute(
                "SELECT 1 FROM products WHERE name = %s AND id <> %s",
                (name, exclude_id),
            )
        return self._cursor.fetchone() is not None

    # ----------------
    # Mutations
    # ----------------

    def create(
        self,
        *,
        category_id: int,
        name: str,
        description: str,
        type_id: Optional[int] = None,
        collection_id: Optional[int] = None,
        default_size_id: Optional[int] = None,
    ) -> int:
        """Insert a product and return its new ID."""
        self._cursor.execute(
            "INSERT INTO products "
            "(category_id, type_id, collection_id, default_size_id, name, description) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                category_id,
                type_id,
                collection_id,
                default_size_id,
                name,
                description,
            ),
        )
        return self._cursor.lastrowid

    def update(
        self,
        product_id: int,
        *,
        category_id: int,
        name: str,
        description: str,
        type_id: Optional[int] = None,
        collection_id: Optional[int] = None,
        default_size_id: Optional[int] = None,
    ) -> None:
        """Overwrite a product's own fields (not its sizes or variants)."""
        self._cursor.execute(
            "UPDATE products SET category_id = %s, type_id = %s, collection_id = %s, "
            "default_size_id = %s, name = %s, description = %s WHERE id = %s",
            (
                category_id,
                type_id,
                collection_id,
                default_size_id,
                name,
                description,
                product_id,
            ),
        )

    def delete(self, product_id: int) -> None:
        """Delete a product and everything hanging off it.

        The schema has no foreign keys, so the rows a cascade would remove are
        removed explicitly here — otherwise they would linger as orphans.
        """
        self._cursor.execute(
            "DELETE FROM product_images WHERE product_id = %s", (product_id,)
        )
        self._cursor.execute(
            "DELETE FROM product_sizes WHERE product_id = %s", (product_id,)
        )
        self._cursor.execute(
            "DELETE FROM product_variants WHERE product_id = %s", (product_id,)
        )
        self._cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))

    # ----------------
    # Sizes a product is available in
    # ----------------

    def get_sizes(self, product_id: int) -> list[dict]:
        """Return the sizes a product is available in, in display order."""
        self._cursor.execute(
            "SELECT s.id, s.name, s.position FROM product_sizes ps "
            "JOIN sizes s ON ps.size_id = s.id "
            "WHERE ps.product_id = %s ORDER BY s.position, s.id",
            (product_id,),
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def set_sizes(self, product_id: int, size_ids: list[int]) -> None:
        """Replace a product's available sizes with exactly `size_ids`."""
        self._cursor.execute(
            "DELETE FROM product_sizes WHERE product_id = %s", (product_id,)
        )
        for size_id in dict.fromkeys(size_ids):
            self._cursor.execute(
                "INSERT INTO product_sizes (product_id, size_id) VALUES (%s, %s)",
                (product_id, size_id),
            )

    # ----------------
    # Internals
    # ----------------

    def _attach_sizes(self, products: list[dict]) -> None:
        """Populate `sizes` for a whole page in one query."""
        if not products:
            return

        ids = [p["id"] for p in products]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT ps.product_id, s.id, s.name, s.position FROM product_sizes ps "
            "JOIN sizes s ON ps.size_id = s.id "
            f"WHERE ps.product_id IN ({placeholders}) "
            "ORDER BY ps.product_id, s.position, s.id",
            ids,
        )

        by_product: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_product[row["product_id"]].append(
                {"id": row["id"], "name": row["name"], "position": row["position"]}
            )

        for product in products:
            product["sizes"] = by_product[product["id"]]

    def _attach_variants(self, products: list[dict]) -> None:
        """Populate `variants` (with nested colour sets) for a whole page."""
        if not products:
            return

        ids = [p["id"] for p in products]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT v.id AS variant_id, v.product_id, "
            "       cs.id AS color_set_id, cs.name AS color_set_name, "
            "       col.id AS collection_id, col.name AS collection_name "
            "FROM product_variants v "
            "JOIN color_sets cs ON v.color_set_id = cs.id "
            "LEFT JOIN collections col ON cs.collection_id = col.id "
            f"WHERE v.product_id IN ({placeholders}) "
            "ORDER BY v.product_id, v.id",
            ids,
        )
        rows = self._cursor.fetchall()

        variants_by_product: dict[int, list] = {i: [] for i in ids}
        by_color_set: dict[int, list] = {}
        for row in rows:
            variant = {
                "id": row["variant_id"],
                "color_set": {
                    "id": row["color_set_id"],
                    "name": row["color_set_name"],
                    "collection": (
                        {"id": row["collection_id"], "name": row["collection_name"]}
                        if row["collection_id"] is not None
                        else None
                    ),
                    "colors": [],
                },
            }
            variants_by_product[row["product_id"]].append(variant)
            by_color_set.setdefault(row["color_set_id"], []).append(variant)

        self._attach_colors_to_variants(by_color_set)

        for product in products:
            product["variants"] = variants_by_product[product["id"]]

    def _attach_images(self, products: list[dict]) -> None:
        """Populate product-level `images`, per-variant images and `primary_image`.

        `primary_image` is what a listing grid shows: the first product-level
        photo, falling back to the first photo of the first variant that has
        one, so a product photographed only per colour set still has a tile.
        """
        if not products:
            return

        from api.repositories.images import ProductImageRepository

        images = ProductImageRepository(self._cursor)

        by_product = images.by_product([p["id"] for p in products])
        variant_ids = [v["id"] for p in products for v in p["variants"]]
        by_variant = images.by_variant(variant_ids)

        for product in products:
            product["images"] = by_product.get(product["id"], [])

            for variant in product["variants"]:
                variant["images"] = by_variant.get(variant["id"], [])

            primary = next(iter(product["images"]), None)
            if primary is None:
                primary = next(
                    (
                        variant["images"][0]
                        for variant in product["variants"]
                        if variant["images"]
                    ),
                    None,
                )
            product["primary_image"] = primary

    def _attach_colors_to_variants(self, by_color_set: dict[int, list]) -> None:
        """Fill in each variant's colour-set colours in one query."""
        if not by_color_set:
            return

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

    @staticmethod
    def _filter(
        search: Optional[str],
        collection_id: Optional[int],
        category_id: Optional[int],
        type_id: Optional[int] = None,
    ) -> Tuple[str, list]:
        clauses, params = [], []

        if term := (search or "").strip():
            # Columns are qualified: an unqualified `name` is ambiguous here.
            clauses.append("(p.name LIKE %s OR c.name LIKE %s OR t.name LIKE %s)")
            params += [f"%{term}%", f"%{term}%", f"%{term}%"]

        if collection_id is not None:
            clauses.append("p.collection_id = %s")
            params.append(collection_id)

        if category_id is not None:
            clauses.append("p.category_id = %s")
            params.append(category_id)

        if type_id is not None:
            # Matching a parent type also returns products filed under its
            # sub-types, so filtering by "Coracao" includes both finishes.
            clauses.append("(p.type_id = %s OR t.parent_id = %s)")
            params += [type_id, type_id]

        return ("WHERE " + " AND ".join(clauses) if clauses else ""), params

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "category": {"id": row["category_id"], "name": row["category_name"]},
            "type": (
                {
                    "id": row["type_id"],
                    "name": row["type_name"],
                    # A sub-type inherits its parent's icon when it has none.
                    "icon": row["type_icon"] or row["type_parent_icon"],
                    "parent": (
                        {
                            "id": row["type_parent_id"],
                            "name": row["type_parent_name"],
                            "icon": row["type_parent_icon"],
                        }
                        if row["type_parent_id"] is not None
                        else None
                    ),
                }
                if row["type_id"] is not None
                else None
            ),
            "collection": (
                {"id": row["collection_id"], "name": row["collection_name"]}
                if row["collection_id"] is not None
                else None
            ),
            "default_size": (
                {
                    "id": row["default_size_id"],
                    "name": row["default_size_name"],
                    "position": row["default_size_position"],
                }
                if row["default_size_id"] is not None
                else None
            ),
            "sizes": [],
            "variants": [],
            "images": [],
            "primary_image": None,
        }
