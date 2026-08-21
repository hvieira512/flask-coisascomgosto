"""Unit tests for the repository layer, driven directly against a cursor."""

import pytest

from repositories import (
    MaterialRepository,
    ProductImageRepository,
    ProductRepository,
    ProductTypeRepository,
    UserRepository,
)


@pytest.fixture()
def materials(cursor):
    return MaterialRepository(cursor)


@pytest.fixture()
def products(cursor):
    return ProductRepository(cursor)


@pytest.fixture()
def wood(cursor):
    """A type id. Every product needs one, so every products test needs this."""
    return ProductTypeRepository(cursor).create(name="Caixa")


@pytest.fixture()
def users(cursor):
    return UserRepository(cursor)


class TestMaterialRepository:
    def test_create_returns_the_new_id(self, materials):
        assert isinstance(materials.create("Madeira"), int)

    def test_get_round_trips_a_created_row(self, materials):
        material_id = materials.create("Madeira")
        assert materials.get(material_id) == {"id": material_id, "name": "Madeira"}

    def test_get_returns_none_when_missing(self, materials):
        assert materials.get(9999) is None

    def test_exists_reflects_reality(self, materials):
        material_id = materials.create("Madeira")
        assert materials.exists(material_id) is True
        assert materials.exists(9999) is False

    def test_name_exists_detects_duplicates(self, materials):
        materials.create("Madeira")
        assert materials.name_exists("Madeira") is True
        assert materials.name_exists("Tecido") is False

    def test_name_exists_can_exclude_one_row(self, materials):
        material_id = materials.create("Madeira")
        assert materials.name_exists("Madeira", exclude_id=material_id) is False

    def test_update_changes_the_name(self, materials):
        material_id = materials.create("Madeira")
        materials.update(material_id, "Tecido")
        assert materials.get(material_id)["name"] == "Tecido"

    def test_delete_removes_the_row(self, materials):
        material_id = materials.create("Madeira")
        materials.delete(material_id)
        assert materials.get(material_id) is None

    def test_list_applies_limit_and_offset(self, materials):
        for name in ["A", "B", "C"]:
            materials.create(name)

        page = materials.list(limit=2, offset=1)
        assert [c["name"] for c in page] == ["B", "C"]

    def test_count_and_list_agree_under_search(self, materials):
        for name in ["Madeira", "Tecido", "Bolos"]:
            materials.create(name)

        assert materials.count(search="Bo") == 1
        assert len(materials.list(search="Bo", limit=10, offset=0)) == 1

    @pytest.mark.parametrize("blank", [None, "", "   "])
    def test_blank_search_is_ignored(self, materials, blank):
        materials.create("Madeira")
        assert materials.count(search=blank) == 1


class TestProductRepository:
    def test_get_nests_the_type_and_material(self, materials, products, wood):
        material_id = materials.create("Madeira")
        product_id = products.create(
            type_id=wood, material_id=material_id, name="Vinho", description="Tinto"
        )

        assert products.get(product_id) == {
            "id": product_id,
            "name": "Vinho",
            "description": "Tinto",
            "material": {"id": material_id, "name": "Madeira"},
            "type": {"id": wood, "name": "Caixa", "icon": None},
            "collection": None,
            "default_size": None,
            "sizes": [],
            "variants": [],
            "images": [],
            "primary_image": None,
        }

    def test_get_returns_none_when_missing(self, products, wood):
        assert products.get(9999) is None

    def test_search_does_not_match_the_material_name(self, materials, products, wood):
        """Material is descriptive, and searching it would surprise: a shopper
        looking for "madeira" wants pieces named that, not every wooden thing."""
        wood_id = materials.create("Madeira")
        products.create(type_id=wood, material_id=wood_id, name="Vinho", description="")

        assert products.list(search="Madeira", limit=10, offset=0) == []

    def test_search_matches_the_product_name(self, materials, products, wood):
        material_id = materials.create("Madeira")
        products.create(type_id=wood, material_id=material_id, name="Vinho", description="")
        products.create(type_id=wood, material_id=material_id, name="Cerveja", description="")

        found = products.list(search="Vin", limit=10, offset=0)
        assert [p["name"] for p in found] == ["Vinho"]

    def test_count_matches_search_results(self, materials, products, wood):
        material_id = materials.create("Madeira")
        products.create(type_id=wood, material_id=material_id, name="Vinho", description="")
        products.create(type_id=wood, material_id=material_id, name="Cerveja", description="")

        assert products.count(search="Vin") == 1
        assert products.count() == 2

    def test_name_exists_can_exclude_one_row(self, materials, products, wood):
        material_id = materials.create("Madeira")
        product_id = products.create(type_id=wood, material_id=material_id, name="Vinho", description=""
        )

        assert products.name_exists("Vinho") is True
        assert products.name_exists("Vinho", exclude_id=product_id) is False

    def test_update_overwrites_fields(self, materials, products, wood):
        bebidas = materials.create("Madeira")
        doces = materials.create("Tecido")
        product_id = products.create(type_id=wood, material_id=bebidas, name="Vinho", description="Tinto"
        )

        products.update(product_id, type_id=wood, material_id=doces, name="Bolo", description="Doce"
        )

        updated = products.get(product_id)
        assert updated["name"] == "Bolo"
        assert updated["material"]["id"] == doces

    def test_delete_removes_the_row(self, materials, products, wood):
        material_id = materials.create("Madeira")
        product_id = products.create(type_id=wood, material_id=material_id, name="V", description="")

        products.delete(product_id)
        assert products.get(product_id) is None

    def test_deleting_a_material_detaches_its_products(
        self, cursor, materials, products, wood
    ):
        """Material is not structural: the piece survives, unclassified."""
        material_id = materials.create("Madeira")
        product_id = products.create(
            type_id=wood, material_id=material_id, name="Vinho", description=""
        )

        materials.delete(material_id)

        assert products.count() == 1
        assert products.get(product_id)["material"] is None
        cursor.execute("SELECT material_id FROM products WHERE id = %s", (product_id,))
        assert cursor.fetchone()["material_id"] is None, "stale material_id left behind"


class TestProductTypeCovers:
    """The landing page's type cards. A type with nothing photographed gets no
    cover and falls back to its icon."""

    @pytest.fixture()
    def types(self, cursor):
        return ProductTypeRepository(cursor)

    @pytest.fixture()
    def images(self, cursor):
        return ProductImageRepository(cursor)

    def test_the_first_photograph_of_the_earliest_piece_wins(
        self, types, products, images
    ):
        box = types.create(name="Caixa")
        first = products.create(type_id=box, name="Caixa alta", description="")
        second = products.create(type_id=box, name="Caixa baixa", description="")
        images.create(product_id=second, url="/second.jpg", position=0)
        images.create(product_id=first, url="/late.jpg", position=3)
        images.create(product_id=first, url="/cover.jpg", alt="Uma caixa", position=1)

        assert types.cover_images([box]) == {
            box: {"url": "/cover.jpg", "alt": "Uma caixa"}
        }

    def test_the_alt_falls_back_to_the_piece_name(self, types, products, images):
        box = types.create(name="Caixa")
        product_id = products.create(type_id=box, name="Caixa de joias", description="")
        images.create(product_id=product_id, url="/x.jpg")

        assert types.cover_images([box])[box]["alt"] == "Caixa de joias"

    def test_a_type_with_no_photographs_is_absent(self, types, products):
        box = types.create(name="Caixa")
        products.create(type_id=box, name="Caixa de joias", description="")

        assert types.cover_images([box]) == {}

    def test_no_types_asks_nothing_of_the_database(self, types):
        assert types.cover_images([]) == {}


class TestUserRepository:
    def test_create_and_get_round_trip(self, users):
        user_id = users.create(
            username="alice", email="alice@example.com", password_hash="hashed"
        )

        user = users.get(user_id)
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"

    def test_get_never_exposes_the_password(self, users):
        user_id = users.create(
            username="alice", email="alice@example.com", password_hash="hashed"
        )
        assert "password" not in users.get(user_id)

    def test_list_never_exposes_the_password(self, users):
        users.create(username="alice", email="a@example.com", password_hash="hashed")
        assert "password" not in users.list(limit=10, offset=0)[0]

    def test_get_credentials_includes_the_hash(self, users):
        users.create(username="alice", email="a@example.com", password_hash="hashed")
        assert users.get_credentials("alice")["password"] == "hashed"

    def test_get_credentials_returns_none_when_missing(self, users):
        assert users.get_credentials("nobody") is None

    def test_an_account_has_no_role(self, users):
        """One kind of account: everyone who can sign in can do everything the
        dashboard offers. The two tests here before this asserted an is_admin flag
        that nothing in the application ever read."""
        user_id = users.create(
            username="alice", email="a@example.com", password_hash="h"
        )
        assert set(users.get(user_id)) == {"id", "username", "email", "created_at"}

    def test_uniqueness_checks(self, users):
        users.create(username="alice", email="a@example.com", password_hash="h")

        assert users.username_exists("alice") is True
        assert users.username_exists("bob") is False
        assert users.email_exists("a@example.com") is True
        assert users.email_exists("b@example.com") is False

    def test_get_by_username(self, users):
        users.create(username="alice", email="a@example.com", password_hash="h")

        assert users.get_by_username("alice")["email"] == "a@example.com"
        assert users.get_by_username("nobody") is None

    def test_count_and_pagination(self, users):
        for name in ["alice", "bob", "carol"]:
            users.create(
                username=name, email=f"{name}@example.com", password_hash="h"
            )

        assert users.count() == 3
        assert [u["username"] for u in users.list(limit=2, offset=1)] == ["bob", "carol"]
