"""HTTP-level tests for /api/materials."""

import pytest


class TestListMaterials:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/materials/").get_json()
        assert body["materials"] == []
        assert body["pagination"] == {"total": 0, "page": 1, "pages": 0, "limit": 10}

    def test_lists_created_materials(self, client, make_material):
        make_material("Madeira")
        make_material("Tecido")

        body = client.get("/api/materials/").get_json()
        assert [c["name"] for c in body["materials"]] == ["Madeira", "Tecido"]
        assert body["pagination"]["total"] == 2

    def test_search_filters_by_partial_name(self, client, make_material):
        make_material("Madeira")
        make_material("Tecido")

        body = client.get("/api/materials/?q=adei").get_json()
        assert [c["name"] for c in body["materials"]] == ["Madeira"]
        assert body["pagination"]["total"] == 1

    def test_search_total_reflects_filter_not_table_size(self, client, make_material):
        for name in ["Madeira", "Tecido", "Cortiça"]:
            make_material(name)

        body = client.get("/api/materials/?q=Cort").get_json()
        assert body["pagination"]["total"] == 1

    def test_pagination_splits_results(self, client, make_material):
        for name in ["A", "B", "C"]:
            make_material(name)

        body = client.get("/api/materials/?page=2&limit=2").get_json()
        assert [c["name"] for c in body["materials"]] == ["C"]
        assert body["pagination"] == {"total": 3, "page": 2, "pages": 2, "limit": 2}

    def test_page_beyond_end_is_empty_not_an_error(self, client, make_material):
        make_material("Madeira")

        response = client.get("/api/materials/?page=99")
        assert response.status_code == 200
        assert response.get_json()["materials"] == []

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0", "?page=0", "?limit=-1"])
    def test_invalid_pagination_returns_400(self, client, query):
        assert client.get(f"/api/materials/{query}").status_code == 400


class TestCreateMaterial:
    def test_creates_and_returns_material(self, client):
        response = client.post("/api/materials/", json={"name": "Madeira"})
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Madeira"
        assert isinstance(body["id"], int)

    def test_duplicate_name_returns_409(self, client, make_material):
        make_material("Madeira")
        assert client.post("/api/materials/", json={"name": "Madeira"}).status_code == 409

    def test_missing_name_returns_400(self, client):
        assert client.post("/api/materials/", json={}).status_code == 400


class TestGetMaterial:
    def test_returns_existing_material(self, client, make_material):
        created = make_material("Madeira")

        body = client.get(f"/api/materials/{created['id']}").get_json()
        assert body == {"id": created["id"], "name": "Madeira"}

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/materials/9999").status_code == 404


class TestUpdateMaterial:
    def test_renames_material(self, client, make_material):
        created = make_material("Madeira")

        response = client.put(
            f"/api/materials/{created['id']}", json={"name": "Madeira Frias"}
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == "Madeira Frias"

    def test_persists_the_rename(self, client, make_material):
        created = make_material("Madeira")
        client.put(f"/api/materials/{created['id']}", json={"name": "Renomeada"})

        assert client.get(f"/api/materials/{created['id']}").get_json()["name"] == "Renomeada"

    def test_unknown_id_returns_404(self, client):
        assert client.put("/api/materials/9999", json={"name": "X"}).status_code == 404

    def test_name_taken_by_another_returns_409(self, client, make_material):
        make_material("Madeira")
        other = make_material("Tecido")

        assert client.put(f"/api/materials/{other['id']}", json={"name": "Madeira"}).status_code == 409

    def test_keeping_own_name_is_allowed(self, client, make_material):
        created = make_material("Madeira")

        assert client.put(f"/api/materials/{created['id']}", json={"name": "Madeira"}).status_code == 200


class TestDeleteMaterial:
    def test_returns_the_deleted_material(self, client, make_material):
        created = make_material("Madeira")

        response = client.delete(f"/api/materials/{created['id']}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Madeira"

    def test_material_is_gone_afterwards(self, client, make_material):
        created = make_material("Madeira")
        client.delete(f"/api/materials/{created['id']}")

        assert client.get(f"/api/materials/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/api/materials/9999").status_code == 404

    def test_deleting_a_material_keeps_its_products(
        self, client, make_material, make_product
    ):
        """Material is descriptive, not structural: a piece does not stop
        existing because the owners tidied the material list."""
        material = make_material("Madeira")
        product = make_product("Vinho", material_id=material["id"])

        client.delete(f"/api/materials/{material['id']}")

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["name"] == "Vinho"
        assert body["material"] is None
