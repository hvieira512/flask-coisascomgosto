"""Unit tests for the repository layer, driven directly against a cursor."""

import pytest

from api.repositories import CategoryRepository, ProductRepository, UserRepository


@pytest.fixture()
def categories(cursor):
    return CategoryRepository(cursor)


@pytest.fixture()
def products(cursor):
    return ProductRepository(cursor)


@pytest.fixture()
def users(cursor):
    return UserRepository(cursor)


class TestCategoryRepository:
    def test_create_returns_the_new_id(self, categories):
        assert isinstance(categories.create("Bebidas"), int)

    def test_get_round_trips_a_created_row(self, categories):
        category_id = categories.create("Bebidas")
        assert categories.get(category_id) == {"id": category_id, "name": "Bebidas"}

    def test_get_returns_none_when_missing(self, categories):
        assert categories.get(9999) is None

    def test_exists_reflects_reality(self, categories):
        category_id = categories.create("Bebidas")
        assert categories.exists(category_id) is True
        assert categories.exists(9999) is False

    def test_name_exists_detects_duplicates(self, categories):
        categories.create("Bebidas")
        assert categories.name_exists("Bebidas") is True
        assert categories.name_exists("Doces") is False

    def test_name_exists_can_exclude_one_row(self, categories):
        category_id = categories.create("Bebidas")
        assert categories.name_exists("Bebidas", exclude_id=category_id) is False

    def test_update_changes_the_name(self, categories):
        category_id = categories.create("Bebidas")
        categories.update(category_id, "Doces")
        assert categories.get(category_id)["name"] == "Doces"

    def test_delete_removes_the_row(self, categories):
        category_id = categories.create("Bebidas")
        categories.delete(category_id)
        assert categories.get(category_id) is None

    def test_list_applies_limit_and_offset(self, categories):
        for name in ["A", "B", "C"]:
            categories.create(name)

        page = categories.list(limit=2, offset=1)
        assert [c["name"] for c in page] == ["B", "C"]

    def test_count_and_list_agree_under_search(self, categories):
        for name in ["Bebidas", "Doces", "Bolos"]:
            categories.create(name)

        assert categories.count(search="Bo") == 1
        assert len(categories.list(search="Bo", limit=10, offset=0)) == 1

    @pytest.mark.parametrize("blank", [None, "", "   "])
    def test_blank_search_is_ignored(self, categories, blank):
        categories.create("Bebidas")
        assert categories.count(search=blank) == 1


class TestProductRepository:
    def test_get_nests_the_category(self, categories, products):
        category_id = categories.create("Bebidas")
        product_id = products.create(
            category_id=category_id, name="Vinho", description="Tinto"
        )

        assert products.get(product_id) == {
            "id": product_id,
            "name": "Vinho",
            "description": "Tinto",
            "category": {"id": category_id, "name": "Bebidas"},
            "type": None,
            "collection": None,
            "default_size": None,
            "sizes": [],
            "variants": [],
            "images": [],
            "primary_image": None,
        }

    def test_get_returns_none_when_missing(self, products):
        assert products.get(9999) is None

    def test_search_matches_the_category_name(self, categories, products):
        bebidas = categories.create("Bebidas")
        doces = categories.create("Doces")
        products.create(category_id=bebidas, name="Vinho", description="")
        products.create(category_id=doces, name="Bolo", description="")

        found = products.list(search="Doces", limit=10, offset=0)
        assert [p["name"] for p in found] == ["Bolo"]

    def test_search_matches_the_product_name(self, categories, products):
        category_id = categories.create("Bebidas")
        products.create(category_id=category_id, name="Vinho", description="")
        products.create(category_id=category_id, name="Cerveja", description="")

        found = products.list(search="Vin", limit=10, offset=0)
        assert [p["name"] for p in found] == ["Vinho"]

    def test_count_matches_search_results(self, categories, products):
        category_id = categories.create("Bebidas")
        products.create(category_id=category_id, name="Vinho", description="")
        products.create(category_id=category_id, name="Cerveja", description="")

        assert products.count(search="Vin") == 1
        assert products.count() == 2

    def test_name_exists_can_exclude_one_row(self, categories, products):
        category_id = categories.create("Bebidas")
        product_id = products.create(
            category_id=category_id, name="Vinho", description=""
        )

        assert products.name_exists("Vinho") is True
        assert products.name_exists("Vinho", exclude_id=product_id) is False

    def test_update_overwrites_fields(self, categories, products):
        bebidas = categories.create("Bebidas")
        doces = categories.create("Doces")
        product_id = products.create(
            category_id=bebidas, name="Vinho", description="Tinto"
        )

        products.update(
            product_id, category_id=doces, name="Bolo", description="Doce"
        )

        updated = products.get(product_id)
        assert updated["name"] == "Bolo"
        assert updated["category"]["id"] == doces

    def test_delete_removes_the_row(self, categories, products):
        category_id = categories.create("Bebidas")
        product_id = products.create(category_id=category_id, name="V", description="")

        products.delete(product_id)
        assert products.get(product_id) is None

    def test_deleting_a_category_cascades(self, cursor, categories, products):
        category_id = categories.create("Bebidas")
        products.create(category_id=category_id, name="Vinho", description="")

        categories.delete(category_id)

        assert products.count() == 0
        cursor.execute("SELECT COUNT(*) AS total FROM products")
        assert cursor.fetchone()["total"] == 0, "orphan row survived the cascade"


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

    def test_is_admin_is_returned_as_a_bool(self, users):
        user_id = users.create(
            username="root", email="r@example.com", password_hash="h", is_admin=True
        )
        assert users.get(user_id)["is_admin"] is True

    def test_defaults_to_non_admin(self, users):
        user_id = users.create(
            username="alice", email="a@example.com", password_hash="h"
        )
        assert users.get(user_id)["is_admin"] is False

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
