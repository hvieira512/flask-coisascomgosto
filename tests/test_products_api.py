"""HTTP-level tests for /api/products."""

import pytest


class TestListProducts:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/products/").get_json()
        assert body["products"] == []
        assert body["pagination"]["total"] == 0

    def test_product_is_returned_with_nested_category(self, client, make_category, make_product):
        category = make_category("Bebidas")
        make_product("Vinho", category_id=category["id"])

        product = client.get("/api/products/").get_json()["products"][0]
        assert product["name"] == "Vinho"
        assert product["category"] == {"id": category["id"], "name": "Bebidas"}

    def test_search_matches_product_name(self, client, make_product):
        make_product("Vinho")
        make_product("Cerveja", category_id=None)

        body = client.get("/api/products/?q=Vin").get_json()
        assert [p["name"] for p in body["products"]] == ["Vinho"]

    def test_search_matches_category_name(self, client, make_category, make_product):
        bebidas = make_category("Bebidas")
        doces = make_category("Doces")
        make_product("Vinho", category_id=bebidas["id"])
        make_product("Bolo", category_id=doces["id"])

        body = client.get("/api/products/?q=Doces").get_json()
        assert [p["name"] for p in body["products"]] == ["Bolo"]

    def test_search_does_not_500_on_the_joined_query(self, client, make_product):
        """Regression: an unqualified `name` was ambiguous across the join."""
        make_product("Vinho")

        assert client.get("/api/products/?q=Vinho").status_code == 200

    def test_search_total_reflects_filter(self, client, make_product):
        make_product("Vinho")
        make_product("Cerveja", category_id=None)

        assert client.get("/api/products/?q=Vin").get_json()["pagination"]["total"] == 1

    def test_pagination_splits_results(self, client, make_category, make_product):
        category = make_category("Bebidas")
        for name in ["A", "B", "C"]:
            make_product(name, category_id=category["id"])

        body = client.get("/api/products/?page=2&limit=2").get_json()
        assert [p["name"] for p in body["products"]] == ["C"]
        assert body["pagination"] == {"total": 3, "page": 2, "pages": 2, "limit": 2}

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0", "?page=0"])
    def test_invalid_pagination_returns_400(self, client, query):
        assert client.get(f"/api/products/{query}").status_code == 400


class TestCreateProduct:
    def test_creates_and_returns_product(self, client, make_category):
        category = make_category("Bebidas")

        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Tinto", "category_id": category["id"]},
        )
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Vinho"
        assert body["description"] == "Tinto"
        assert body["category"]["name"] == "Bebidas"

    def test_unknown_category_returns_404(self, client):
        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Tinto", "category_id": 9999},
        )
        assert response.status_code == 404

    def test_duplicate_name_returns_409(self, client, make_category, make_product):
        category = make_category("Bebidas")
        make_product("Vinho", category_id=category["id"])

        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Outro", "category_id": category["id"]},
        )
        assert response.status_code == 409

    @pytest.mark.parametrize(
        "payload",
        [
            {"description": "Tinto", "category_id": 1},
            {"name": "Vinho", "category_id": 1},
            {"name": "Vinho", "description": "Tinto"},
            {},
        ],
    )
    def test_missing_fields_return_400(self, client, make_category, payload):
        make_category("Bebidas")
        assert client.post("/api/products/", json=payload).status_code == 400


class TestGetProduct:
    def test_returns_existing_product(self, client, make_product):
        created = make_product("Vinho")

        body = client.get(f"/api/products/{created['id']}").get_json()
        assert body["name"] == "Vinho"

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/products/9999").status_code == 404


class TestUpdateProduct:
    def test_updates_all_fields(self, client, make_category, make_product):
        created = make_product("Vinho")
        other = make_category("Doces")

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Bolo", "description": "Doce", "category_id": other["id"]},
        )
        assert response.status_code == 200

        body = response.get_json()
        assert body["name"] == "Bolo"
        assert body["description"] == "Doce"
        assert body["category"]["name"] == "Doces"

    def test_unknown_product_returns_404(self, client, make_category):
        category = make_category("Bebidas")

        response = client.put(
            "/api/products/9999",
            json={"name": "Ghost", "description": "d", "category_id": category["id"]},
        )
        assert response.status_code == 404

    def test_unknown_product_does_not_return_a_null_body(self, client, make_category):
        """Regression: a missing product used to marshal to 200 with all-null fields."""
        category = make_category("Bebidas")

        response = client.put(
            "/api/products/9999",
            json={"name": "Ghost", "description": "d", "category_id": category["id"]},
        )
        assert response.get_json().get("id") is None
        assert response.status_code != 200

    def test_unknown_category_returns_404(self, client, make_product):
        created = make_product("Vinho")

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Vinho", "description": "d", "category_id": 9999},
        )
        assert response.status_code == 404

    def test_name_taken_by_another_returns_409(self, client, make_category, make_product):
        category = make_category("Bebidas")
        make_product("Vinho", category_id=category["id"])
        other = make_product("Cerveja", category_id=category["id"])

        response = client.put(
            f"/api/products/{other['id']}",
            json={"name": "Vinho", "description": "d", "category_id": category["id"]},
        )
        assert response.status_code == 409

    def test_keeping_own_name_is_allowed(self, client, make_category, make_product):
        category = make_category("Bebidas")
        created = make_product("Vinho", category_id=category["id"])

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Vinho", "description": "novo", "category_id": category["id"]},
        )
        assert response.status_code == 200

    def test_partial_payload_returns_400(self, client, make_product):
        """Regression: PUT lacked validate=True, so a partial body raised KeyError."""
        created = make_product("Vinho")

        assert client.put(f"/api/products/{created['id']}", json={"name": "x"}).status_code == 400


class TestDeleteProduct:
    def test_returns_the_deleted_product(self, client, make_product):
        created = make_product("Vinho")

        response = client.delete(f"/api/products/{created['id']}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Vinho"

    def test_product_is_gone_afterwards(self, client, make_product):
        created = make_product("Vinho")
        client.delete(f"/api/products/{created['id']}")

        assert client.get(f"/api/products/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/api/products/9999").status_code == 404

    def test_404_message_names_the_product_not_a_category(self, client):
        """Regression: the message used to read 'Category #... not found'."""
        body = client.delete("/api/products/9999").get_json()
        assert "product" in body["message"].lower()


class TestDashboardFilterQueries:
    """The dashboard filter bar sends these; they must narrow, not error.

    Filtering on photographs has no endpoint and is applied to the fetched page
    in fetch.js, so it is deliberately absent here.
    """

    def test_search_narrows_by_name(self, client, make_product):
        make_product("Bastidor Bordado")
        make_product("Caixa Redonda")

        body = client.get("/api/products/?q=bastidor&limit=100").get_json()
        assert [p["name"] for p in body["products"]] == ["Bastidor Bordado"]

    def test_type_filter_includes_sub_types(self, client, make_product,
                                            make_product_type):
        parent = make_product_type("Caixa")
        sub = make_product_type("Caixa redonda", parent_id=parent["id"])
        make_product("Caixa Redonda Filigrana", type_id=sub["id"])
        make_product("Outra")

        by_parent = client.get(
            f"/api/products/?type_id={parent['id']}&limit=100").get_json()
        assert [p["name"] for p in by_parent["products"]] == ["Caixa Redonda Filigrana"]

    def test_collection_filter_narrows(self, client, make_product, make_collection):
        collection = make_collection("Bordados")
        make_product("Bastidor", collection_id=collection["id"])
        make_product("Sem colecção")

        body = client.get(
            f"/api/products/?collection_id={collection['id']}&limit=100").get_json()
        assert [p["name"] for p in body["products"]] == ["Bastidor"]

    def test_filters_combine(self, client, make_product, make_collection):
        collection = make_collection("Bordados")
        make_product("Bastidor Bordado", collection_id=collection["id"])
        make_product("Bastidor Viana", collection_id=collection["id"])

        body = client.get(
            f"/api/products/?collection_id={collection['id']}&q=viana&limit=100"
        ).get_json()
        assert [p["name"] for p in body["products"]] == ["Bastidor Viana"]

    def test_no_match_is_an_empty_page_not_an_error(self, client, make_product):
        make_product("Caixa")

        response = client.get("/api/products/?q=zzzz&limit=100")
        assert response.status_code == 200
        assert response.get_json()["products"] == []
