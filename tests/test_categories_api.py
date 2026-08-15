"""HTTP-level tests for /api/categories."""

import pytest


class TestListCategories:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/categories/").get_json()
        assert body["categories"] == []
        assert body["pagination"] == {"total": 0, "page": 1, "pages": 0, "limit": 10}

    def test_lists_created_categories(self, client, make_category):
        make_category("Bebidas")
        make_category("Doces")

        body = client.get("/api/categories/").get_json()
        assert [c["name"] for c in body["categories"]] == ["Bebidas", "Doces"]
        assert body["pagination"]["total"] == 2

    def test_search_filters_by_partial_name(self, client, make_category):
        make_category("Bebidas")
        make_category("Doces")

        body = client.get("/api/categories/?q=ebid").get_json()
        assert [c["name"] for c in body["categories"]] == ["Bebidas"]
        assert body["pagination"]["total"] == 1

    def test_search_total_reflects_filter_not_table_size(self, client, make_category):
        for name in ["Bebidas", "Doces", "Bolos"]:
            make_category(name)

        body = client.get("/api/categories/?q=Bo").get_json()
        assert body["pagination"]["total"] == 1

    def test_pagination_splits_results(self, client, make_category):
        for name in ["A", "B", "C"]:
            make_category(name)

        body = client.get("/api/categories/?page=2&limit=2").get_json()
        assert [c["name"] for c in body["categories"]] == ["C"]
        assert body["pagination"] == {"total": 3, "page": 2, "pages": 2, "limit": 2}

    def test_page_beyond_end_is_empty_not_an_error(self, client, make_category):
        make_category("Bebidas")

        response = client.get("/api/categories/?page=99")
        assert response.status_code == 200
        assert response.get_json()["categories"] == []

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0", "?page=0", "?limit=-1"])
    def test_invalid_pagination_returns_400(self, client, query):
        assert client.get(f"/api/categories/{query}").status_code == 400


class TestCreateCategory:
    def test_creates_and_returns_category(self, client):
        response = client.post("/api/categories/", json={"name": "Bebidas"})
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Bebidas"
        assert isinstance(body["id"], int)

    def test_duplicate_name_returns_409(self, client, make_category):
        make_category("Bebidas")
        assert client.post("/api/categories/", json={"name": "Bebidas"}).status_code == 409

    def test_missing_name_returns_400(self, client):
        assert client.post("/api/categories/", json={}).status_code == 400


class TestGetCategory:
    def test_returns_existing_category(self, client, make_category):
        created = make_category("Bebidas")

        body = client.get(f"/api/categories/{created['id']}").get_json()
        assert body == {"id": created["id"], "name": "Bebidas"}

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/categories/9999").status_code == 404


class TestUpdateCategory:
    def test_renames_category(self, client, make_category):
        created = make_category("Bebidas")

        response = client.put(
            f"/api/categories/{created['id']}", json={"name": "Bebidas Frias"}
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == "Bebidas Frias"

    def test_persists_the_rename(self, client, make_category):
        created = make_category("Bebidas")
        client.put(f"/api/categories/{created['id']}", json={"name": "Renomeada"})

        assert client.get(f"/api/categories/{created['id']}").get_json()["name"] == "Renomeada"

    def test_unknown_id_returns_404(self, client):
        assert client.put("/api/categories/9999", json={"name": "X"}).status_code == 404

    def test_name_taken_by_another_returns_409(self, client, make_category):
        make_category("Bebidas")
        other = make_category("Doces")

        assert client.put(f"/api/categories/{other['id']}", json={"name": "Bebidas"}).status_code == 409

    def test_keeping_own_name_is_allowed(self, client, make_category):
        created = make_category("Bebidas")

        assert client.put(f"/api/categories/{created['id']}", json={"name": "Bebidas"}).status_code == 200


class TestDeleteCategory:
    def test_returns_the_deleted_category(self, client, make_category):
        created = make_category("Bebidas")

        response = client.delete(f"/api/categories/{created['id']}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Bebidas"

    def test_category_is_gone_afterwards(self, client, make_category):
        created = make_category("Bebidas")
        client.delete(f"/api/categories/{created['id']}")

        assert client.get(f"/api/categories/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/api/categories/9999").status_code == 404

    def test_deleting_a_category_cascades_to_its_products(
        self, client, make_category, make_product
    ):
        category = make_category("Bebidas")
        make_product("Vinho", category_id=category["id"])

        client.delete(f"/api/categories/{category['id']}")

        assert client.get("/api/products/").get_json()["pagination"]["total"] == 0
