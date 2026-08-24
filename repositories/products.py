"""Data access for the products table."""

from __future__ import annotations

from typing import Optional, Tuple

from pymysql.cursors import DictCursor

from repositories.base import one_row

# Every read resolves the type (required) plus the optional default size, so
# callers get one consistent product shape. The type join is inner because
# type_id is NOT NULL. Neither the materials nor the collections are here: a piece
# may be made of several materials, and it is in a collection only through the
# colour sets it is offered in, so both arrive per page the way the sizes do.
_FROM = """
    FROM products p
    JOIN product_types t ON p.type_id = t.id
    LEFT JOIN sizes s ON p.default_size_id = s.id
"""

_SELECT = f"""
    SELECT
        p.id AS id,
        p.name AS name,
        p.description AS description,
        s.id AS default_size_id,
        s.name AS default_size_name,
        s.position AS default_size_position,
        t.id AS type_id,
        t.name AS type_name,
        t.icon AS type_icon
    {_FROM}
"""


def _as_ids(value) -> list[int]:
    """One id, a list of them, or nothing at all — callers pass whichever they
    have and the filter builder sees a list either way."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [int(v) for v in value if v is not None]
    return [int(value)]


class ProductRepository:
    """All SQL touching products, product_sizes and product_variants lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(
        self,
        *,
        search: Optional[str] = None,
        collection_id: Optional[int | list[int]] = None,
        material_id: Optional[int | list[int]] = None,
        type_id: Optional[int | list[int]] = None,
        limit: int,
        offset: int,
        photographed_first: bool = False,
    ) -> list[dict]:
        """`photographed_first` is the storefront's order: a shopper scanning a
        grid should not have to page past pieces with nothing to look at. The
        dashboard keeps insertion order, where an unphotographed piece is the
        one the owners are looking for."""
        where, params = self._filter(search, collection_id, material_id, type_id)
        order = "p.id"
        if photographed_first:
            order = (
                "EXISTS (SELECT 1 FROM product_images i WHERE i.product_id = p.id "
                "AND i.deleted_at IS NULL) DESC, p.id"
            )
        self._cursor.execute(
            f"{_SELECT} {where} ORDER BY {order} LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        products = [self._to_dict(row) for row in self._cursor.fetchall()]
        self._attach_collections(products)
        self._attach_materials(products)
        self._attach_sizes(products)
        self._attach_variants(products)
        self._attach_images(products)
        return products

    def count(
        self,
        *,
        search: Optional[str] = None,
        collection_id: Optional[int | list[int]] = None,
        material_id: Optional[int | list[int]] = None,
        type_id: Optional[int | list[int]] = None,
    ) -> int:
        where, params = self._filter(search, collection_id, material_id, type_id)
        self._cursor.execute(f"SELECT COUNT(*) AS total {_FROM} {where}", params)
        return one_row(self._cursor)["total"]

    def get(self, product_id: int) -> Optional[dict]:
        """Return a product with its type, material, sizes and variants."""
        self._cursor.execute(f"{_SELECT} WHERE p.id = %s", (product_id,))
        row = self._cursor.fetchone()
        if not row:
            return None

        product = self._to_dict(row)
        self._attach_collections([product])
        self._attach_materials([product])
        self._attach_sizes([product])
        self._attach_variants([product])
        self._attach_images([product])
        return product

    def exists(self, product_id: int) -> bool:
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

    def create(
        self,
        *,
        type_id: int,
        name: str,
        description: str,
        default_size_id: Optional[int] = None,
    ) -> int:
        self._cursor.execute(
            "INSERT INTO products "
            "(type_id, default_size_id, name, description) "
            "VALUES (%s, %s, %s, %s)",
            (
                type_id,
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
        type_id: int,
        name: str,
        description: str,
        default_size_id: Optional[int] = None,
    ) -> None:
        """Overwrite a product's own fields (not its materials, sizes, variants,
        or the collections its colours put it in)."""
        self._cursor.execute(
            "UPDATE products SET type_id = %s, "
            "default_size_id = %s, name = %s, description = %s WHERE id = %s",
            (
                type_id,
                default_size_id,
                name,
                description,
                product_id,
            ),
        )

    def delete(self, product_id: int) -> None:
        """Delete a product and everything hanging off it.

        ON DELETE CASCADE would remove the child rows on its own; they are removed
        here as well so the behaviour is stated where it is decided. The
        photographs' files are not touched — uploads.sweep() collects them once
        nothing points at them, which is what makes deleting a piece by mistake
        survivable.
        """
        self._cursor.execute(
            "DELETE FROM product_images WHERE product_id = %s", (product_id,)
        )
        self._cursor.execute(
            "DELETE FROM product_materials WHERE product_id = %s", (product_id,)
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

    # ----------------
    # What a piece is made of
    # ----------------

    def get_materials(self, product_id: int) -> list[dict]:
        self._cursor.execute(
            "SELECT m.id, m.name FROM product_materials pm "
            "JOIN materials m ON pm.material_id = m.id "
            "WHERE pm.product_id = %s ORDER BY m.name",
            (product_id,),
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def set_materials(self, product_id: int, material_ids: list[int]) -> None:
        """Replace what a piece is made of with exactly `material_ids`."""
        self._cursor.execute(
            "DELETE FROM product_materials WHERE product_id = %s", (product_id,)
        )
        for material_id in dict.fromkeys(material_ids):
            self._cursor.execute(
                "INSERT INTO product_materials (product_id, material_id) "
                "VALUES (%s, %s)",
                (product_id, material_id),
            )

    def _attach_materials(self, products: list[dict]) -> None:
        """Populate `materials` for a whole page in one query."""
        if not products:
            return

        ids = [p["id"] for p in products]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT pm.product_id, m.id, m.name FROM product_materials pm "
            "JOIN materials m ON pm.material_id = m.id "
            f"WHERE pm.product_id IN ({placeholders}) "
            "ORDER BY pm.product_id, m.name",
            ids,
        )

        by_product: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_product[row["product_id"]].append(
                {"id": row["id"], "name": row["name"]}
            )

        for product in products:
            product["materials"] = by_product[product["id"]]

    # ----------------
    # The collections a piece is in, which is a fact about its colours
    # ----------------

    def _attach_collections(self, products: list[dict]) -> None:
        """Populate `collections` for a whole page in one query.

        A collection gathers colour sets, and a piece is offered in colour sets, so
        this is the only path there is: collection -> colour set -> variant ->
        piece. DISTINCT because two of a piece's colourways may be gathered by the
        same collection, and that is still one collection.
        """
        if not products:
            return

        ids = [p["id"] for p in products]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT DISTINCT v.product_id, col.id, col.name "
            "FROM product_variants v "
            "JOIN collection_color_sets ccs ON ccs.color_set_id = v.color_set_id "
            "JOIN collections col ON col.id = ccs.collection_id "
            f"WHERE v.product_id IN ({placeholders}) "
            "ORDER BY v.product_id, col.name",
            ids,
        )

        by_product: dict[int, list] = {i: [] for i in ids}
        for row in self._cursor.fetchall():
            by_product[row["product_id"]].append(
                {"id": row["id"], "name": row["name"]}
            )

        for product in products:
            product["collections"] = by_product[product["id"]]

    def _attach_variants(self, products: list[dict]) -> None:
        """Populate `variants` (with nested colour sets) for a whole page."""
        if not products:
            return

        ids = [p["id"] for p in products]
        placeholders = ", ".join(["%s"] * len(ids))
        self._cursor.execute(
            "SELECT v.id AS variant_id, v.product_id, "
            "       cs.id AS color_set_id, cs.name AS color_set_name "
            "FROM product_variants v "
            "JOIN color_sets cs ON v.color_set_id = cs.id "
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
                    "colors": [],
                },
            }
            variants_by_product[row["product_id"]].append(variant)
            by_color_set.setdefault(row["color_set_id"], []).append(variant)

        self._attach_colors_to_variants(by_color_set)

        for product in products:
            product["variants"] = variants_by_product[product["id"]]

    def _attach_images(self, products: list[dict]) -> None:
        """Populate each variant's images and the product's `primary_image`.

        Every photograph belongs to a colour: a piece looks different in each
        colourway, so a photo that belonged to the product as a whole could only
        ever be a stand-in for one of them. `primary_image` is what a listing
        grid shows — the first photograph of the first colour that has one.
        """
        if not products:
            return

        from repositories.images import ProductImageRepository

        images = ProductImageRepository(self._cursor)
        variant_ids = [v["id"] for p in products for v in p["variants"]]
        by_variant = images.by_variant(variant_ids)

        for product in products:
            for variant in product["variants"]:
                variant["images"] = by_variant.get(variant["id"], [])

            product["primary_image"] = next(
                (
                    variant["images"][0]
                    for variant in product["variants"]
                    if variant["images"]
                ),
                None,
            )

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
        collection_id: Optional[int | list[int]],
        material_id: Optional[int | list[int]],
        type_id: Optional[int | list[int]] = None,
    ) -> Tuple[str, list]:
        """Each id filter takes one value or several. Several read as OR — a
        shopper ticking Caixa and Moldura wants both families, not the pieces
        that are somehow each — while separate filters still narrow with AND."""
        clauses, params = [], []

        if term := (search or "").strip():
            # Columns are qualified: an unqualified `name` is ambiguous here.
            clauses.append("(p.name LIKE %s OR t.name LIKE %s)")
            params += [f"%{term}%", f"%{term}%"]

        ids = _as_ids(type_id)
        if ids:
            placeholders = ", ".join(["%s"] * len(ids))
            clauses.append(f"p.type_id IN ({placeholders})")
            params += ids

        # A collection reaches a piece through the piece's colour sets, so this is
        # EXISTS down that path rather than a column on the product. Same reason as
        # the materials below: a piece in a collection twice over — two of its
        # colourways gathered by it — must still be one row.
        if ids := _as_ids(collection_id):
            placeholders = ", ".join(["%s"] * len(ids))
            clauses.append(
                "EXISTS (SELECT 1 FROM product_variants v "
                "        JOIN collection_color_sets ccs"
                "          ON ccs.color_set_id = v.color_set_id "
                f"WHERE v.product_id = p.id AND ccs.collection_id IN ({placeholders}))"
            )
            params += ids

        # Materials hang off a join, so this is EXISTS rather than IN: a piece
        # made of wood and modelling paste has two rows, and matching them with a
        # JOIN would return the piece twice.
        if ids := _as_ids(material_id):
            placeholders = ", ".join(["%s"] * len(ids))
            clauses.append(
                "EXISTS (SELECT 1 FROM product_materials pm "
                f"WHERE pm.product_id = p.id AND pm.material_id IN ({placeholders}))"
            )
            params += ids

        return ("WHERE " + " AND ".join(clauses) if clauses else ""), params

    def facet_counts(self) -> dict[str, list[dict]]:
        """How many pieces sit behind each filter option, so the sidebar can say
        so before it is clicked. Deliberately unfiltered: a count that moved
        every time another filter changed would be a different question."""
        self._cursor.execute(
            "SELECT type_id AS id, COUNT(*) AS count FROM products "
            "GROUP BY type_id"
        )
        facets = {"types": [dict(row) for row in self._cursor.fetchall()]}

        # Counted down the same path the filter takes, and DISTINCT because a piece
        # whose two colourways are both in a collection is one piece in it.
        self._cursor.execute(
            "SELECT ccs.collection_id AS id, COUNT(DISTINCT v.product_id) AS count "
            "FROM collection_color_sets ccs "
            "JOIN product_variants v ON v.color_set_id = ccs.color_set_id "
            "GROUP BY ccs.collection_id"
        )
        facets["collections"] = [dict(row) for row in self._cursor.fetchall()]

        # A piece made of two materials counts under both, so these can add up to
        # more than the catalogue holds. That is the honest answer to "how many
        # pieces are made of wood", and the pages that show it say so.
        self._cursor.execute(
            "SELECT material_id AS id, COUNT(*) AS count "
            "FROM product_materials GROUP BY material_id"
        )
        facets["materials"] = [dict(row) for row in self._cursor.fetchall()]
        return facets

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "type": (
                {
                    "id": row["type_id"],
                    "name": row["type_name"],
                    "icon": row["type_icon"],
                }
                if row["type_id"] is not None
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
            "collections": [],
            "materials": [],
            "sizes": [],
            "variants": [],
            "primary_image": None,
        }
