"""The foreign keys, and whether they say the same thing as the repositories.

Every constraint added in migration 0006 restates a cascade the repository layer
already performs. Two statements of one rule drift unless something compares
them, and drift here is the bad kind: the repository would do one thing and a
direct DELETE another, which is exactly the confusion the constraints were added
to remove.

So these tests go around the repositories on purpose. A plain DELETE is the case
the constraints exist for — the manual SQL session, the future script, the
endpoint somebody writes without reading this file.
"""

import pytest
from pymysql.err import IntegrityError

# What the repository layer does, and what the constraint has to agree with.
# Kept as data so a new relationship without a rule shows up as a missing row
# rather than as nothing at all.
EXPECTED_RULES = {
    ("products", "type_id"): "RESTRICT",
    ("products", "material_id"): "SET NULL",
    ("products", "collection_id"): "SET NULL",
    ("products", "default_size_id"): "SET NULL",
    ("color_sets", "collection_id"): "SET NULL",
    ("color_set_colors", "color_set_id"): "CASCADE",
    ("color_set_colors", "color_id"): "CASCADE",
    ("product_variants", "product_id"): "CASCADE",
    ("product_variants", "color_set_id"): "CASCADE",
    ("product_images", "product_id"): "CASCADE",
    ("product_images", "variant_id"): "CASCADE",
    ("product_sizes", "product_id"): "CASCADE",
    ("product_sizes", "size_id"): "CASCADE",
}


def _rules(cursor) -> dict:
    cursor.execute(
        """
        SELECT rc.delete_rule AS rule, kcu.table_name AS tbl, kcu.column_name AS col
        FROM information_schema.referential_constraints rc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = rc.constraint_name
         AND kcu.constraint_schema = rc.constraint_schema
        WHERE rc.constraint_schema = DATABASE()
        """
    )
    return {(row["tbl"], row["col"]): row["rule"] for row in cursor.fetchall()}


class TestEveryRelationshipIsDeclared:
    def test_the_rules_are_exactly_what_the_repositories_do(self, cursor):
        assert _rules(cursor) == EXPECTED_RULES

    def test_schema_sql_declares_what_the_migration_declares(self, cursor):
        """The two are written by hand and separately: schema.sql builds a fresh
        database, the migration upgrades an existing one. A constraint added to
        only one of them means `init-db` and `migrate` produce different schemas,
        which is the kind of difference that surfaces months later.

        This database was built from schema.sql, so the constraint names it holds
        are what schema.sql declares."""
        from pathlib import Path
        import re

        migration = (
            Path(__file__).parent.parent / "db/migrations/0006_foreign_keys.sql"
        ).read_text()
        declared = set(re.findall(r"CONSTRAINT (fk_\w+)", migration))

        cursor.execute(
            "SELECT constraint_name AS name FROM information_schema.table_constraints "
            "WHERE constraint_schema = DATABASE() AND constraint_type = 'FOREIGN KEY'"
        )
        in_schema = {row["name"] for row in cursor.fetchall()}

        assert declared == in_schema


class TestTheDatabaseRefusesAnOrphan:
    """Writing a child row whose parent does not exist. Before 0006 every one of
    these succeeded and left a row nothing could reach."""

    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO product_variants (product_id, color_set_id) VALUES (9999, 1)",
            "INSERT INTO product_images (product_id, variant_id, url) "
            "VALUES (9999, 9999, '/x.jpg')",
            "INSERT INTO product_sizes (product_id, size_id) VALUES (9999, 1)",
            "INSERT INTO color_set_colors (color_set_id, color_id) VALUES (9999, 1)",
        ],
    )
    def test_an_invented_parent_is_rejected(self, cursor, sql):
        with pytest.raises(IntegrityError):
            cursor.execute(sql)


class TestDeletingCascadesTheSameWayTheRepositoryWould:
    @pytest.fixture()
    def piece(self, make_product, make_color_set, client):
        """A product with a colour, a photograph and a size — one of each thing
        that hangs off it."""
        product = make_product("Caixa com tudo")
        color_set = make_color_set("Azul e Dourado")

        variant = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        )
        assert variant.status_code == 201, variant.get_json()

        return product, color_set, variant.get_json()

    def test_deleting_a_product_takes_its_variants_with_it(self, cursor, piece):
        product, _, variant = piece

        cursor.execute("DELETE FROM products WHERE id = %s", (product["id"],))

        cursor.execute(
            "SELECT COUNT(*) AS n FROM product_variants WHERE id = %s", (variant["id"],)
        )
        assert cursor.fetchone()["n"] == 0

    def test_deleting_a_colour_set_takes_the_variants_using_it(self, cursor, piece):
        _, color_set, variant = piece

        cursor.execute("DELETE FROM color_sets WHERE id = %s", (color_set["id"],))

        cursor.execute(
            "SELECT COUNT(*) AS n FROM product_variants WHERE id = %s", (variant["id"],)
        )
        assert cursor.fetchone()["n"] == 0

    def test_deleting_a_variant_takes_its_photographs(self, cursor, piece):
        product, _, variant = piece
        cursor.execute(
            "INSERT INTO product_images (product_id, variant_id, url) "
            "VALUES (%s, %s, '/static/img/products/x.jpg')",
            (product["id"], variant["id"]),
        )

        cursor.execute("DELETE FROM product_variants WHERE id = %s", (variant["id"],))

        cursor.execute(
            "SELECT COUNT(*) AS n FROM product_images WHERE variant_id = %s",
            (variant["id"],),
        )
        assert cursor.fetchone()["n"] == 0

    def test_deleting_a_collection_detaches_rather_than_deletes(
        self, cursor, make_collection, make_product
    ):
        """The pieces survive their collection. Losing the catalogue because a
        grouping was renamed away would be the worst possible reading of a
        cascade."""
        collection = make_collection("Inverno")
        product = make_product("Caixa de Inverno", collection_id=collection["id"])

        cursor.execute("DELETE FROM collections WHERE id = %s", (collection["id"],))

        cursor.execute(
            "SELECT collection_id FROM products WHERE id = %s", (product["id"],)
        )
        assert cursor.fetchone()["collection_id"] is None

    def test_deleting_a_material_detaches_rather_than_deletes(
        self, cursor, make_material, make_product
    ):
        material = make_material("Cortiça")
        product = make_product("Caixa de cortiça", material_id=material["id"])

        cursor.execute("DELETE FROM materials WHERE id = %s", (material["id"],))

        cursor.execute("SELECT material_id FROM products WHERE id = %s", (product["id"],))
        assert cursor.fetchone()["material_id"] is None


class TestATypeInUseCannotBeDeleted:
    def test_the_database_refuses_it(self, cursor, make_product_type, make_product):
        """type_id is NOT NULL, so there is no unfiled-piece state — a cascade
        here would delete the owners' work and SET NULL is not available."""
        product_type = make_product_type("Tipo em uso")
        make_product("Peça desse tipo", type_id=product_type["id"])

        with pytest.raises(IntegrityError):
            cursor.execute(
                "DELETE FROM product_types WHERE id = %s", (product_type["id"],)
            )

    def test_the_api_still_answers_409_with_the_count(
        self, client, make_product_type, make_product
    ):
        """The constraint is the backstop; this is what the owners actually see."""
        product_type = make_product_type("Tipo em uso")
        make_product("Peça desse tipo", type_id=product_type["id"])

        response = client.delete(f"/api/product-types/{product_type['id']}")

        assert response.status_code == 409
        assert "1" in response.get_json()["message"]

    def test_an_unused_type_still_goes(self, client, make_product_type):
        product_type = make_product_type("Tipo sem peças")

        assert client.delete(
            f"/api/product-types/{product_type['id']}"
        ).status_code in (200, 204)
