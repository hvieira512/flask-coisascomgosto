"""HTTP-level tests for the catalog layers: collections, colours, colour sets,
sizes and product types."""

import pytest


class TestCollections:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/collections/").get_json()
        assert body["collections"] == []
        assert body["pagination"]["total"] == 0

    def test_create_and_read_back(self, client):
        response = client.post(
            "/api/collections/",
            json={"name": "Barra da Saia", "description": "Regional"},
        )
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Barra da Saia"
        assert body["description"] == "Regional"

    def test_description_is_optional(self, client):
        response = client.post("/api/collections/", json={"name": "Minimal"})
        assert response.status_code == 201
        assert response.get_json()["description"] is None

    def test_duplicate_name_returns_409(self, client, make_collection):
        make_collection("Barra da Saia")
        assert (
            client.post("/api/collections/", json={"name": "Barra da Saia"}).status_code
            == 409
        )

    def test_missing_name_returns_400(self, client):
        assert client.post("/api/collections/", json={}).status_code == 400

    def test_update_renames(self, client, make_collection):
        created = make_collection("Barra da Saia")
        response = client.put(
            f"/api/collections/{created['id']}", json={"name": "Renamed"}
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == "Renamed"

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/collections/9999").status_code == 404
        assert client.put("/api/collections/9999", json={"name": "X"}).status_code == 404
        assert client.delete("/api/collections/9999").status_code == 404

    def test_search_filters_by_name(self, client, make_collection):
        make_collection("Barra da Saia")
        make_collection("Lenco dos Namorados")

        body = client.get("/api/collections/?q=Barra").get_json()
        assert [c["name"] for c in body["collections"]] == ["Barra da Saia"]

    def test_deleting_a_collection_leaves_its_products(
        self, client, make_collection, make_product
    ):
        collection = make_collection("Barra da Saia")
        product = make_product("Caixa", collection_id=collection["id"])

        client.delete(f"/api/collections/{collection['id']}")

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["collection"] is None


class TestColors:
    def test_create_with_hex(self, client):
        response = client.post("/api/colors/", json={"name": "White", "hex": "#FFFFFF"})
        assert response.status_code == 201
        assert response.get_json()["hex"] == "#FFFFFF"

    def test_hex_is_optional(self, client):
        response = client.post("/api/colors/", json={"name": "Green"})
        assert response.status_code == 201
        assert response.get_json()["hex"] is None

    def test_duplicate_name_returns_409(self, client, make_color):
        make_color("White")
        assert client.post("/api/colors/", json={"name": "White"}).status_code == 409

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/colors/9999").status_code == 404

    def test_deleting_a_colour_removes_it_from_sets(
        self, client, make_color, make_color_set
    ):
        white = make_color("White")
        green = make_color("Green")
        color_set = make_color_set("White and Green", [white["id"], green["id"]])

        client.delete(f"/api/colors/{green['id']}")

        body = client.get(f"/api/color-sets/{color_set['id']}").get_json()
        assert [c["name"] for c in body["colors"]] == ["White"]


class TestColorSets:
    def test_create_with_colours_in_order(self, client, make_color):
        white = make_color("White")
        green = make_color("Green")

        response = client.post(
            "/api/color-sets/",
            json={"name": "White and Green", "color_ids": [white["id"], green["id"]]},
        )
        assert response.status_code == 201
        assert [c["name"] for c in response.get_json()["colors"]] == ["White", "Green"]

    def test_collection_is_optional(self, client, make_color):
        white = make_color("White")
        response = client.post(
            "/api/color-sets/", json={"name": "Just White", "color_ids": [white["id"]]}
        )
        assert response.status_code == 201
        assert response.get_json()["collection"] is None

    def test_nests_its_collection(self, client, make_collection, make_color):
        collection = make_collection("Barra da Saia")
        white = make_color("White")

        response = client.post(
            "/api/color-sets/",
            json={
                "name": "White",
                "color_ids": [white["id"]],
                "collection_id": collection["id"],
            },
        )
        assert response.get_json()["collection"]["name"] == "Barra da Saia"

    def test_unknown_colour_returns_404(self, client):
        response = client.post(
            "/api/color-sets/", json={"name": "Ghost", "color_ids": [9999]}
        )
        assert response.status_code == 404

    def test_unknown_collection_returns_404(self, client, make_color):
        white = make_color("White")
        response = client.post(
            "/api/color-sets/",
            json={"name": "X", "color_ids": [white["id"]], "collection_id": 9999},
        )
        assert response.status_code == 404

    def test_same_name_allowed_in_different_collections(
        self, client, make_collection, make_color
    ):
        first = make_collection("First")
        second = make_collection("Second")
        white = make_color("White")

        payload = {"name": "White and Green", "color_ids": [white["id"]]}
        a = client.post(
            "/api/color-sets/", json={**payload, "collection_id": first["id"]}
        )
        b = client.post(
            "/api/color-sets/", json={**payload, "collection_id": second["id"]}
        )
        assert a.status_code == 201
        assert b.status_code == 201

    def test_duplicate_name_in_same_collection_returns_409(
        self, client, make_collection, make_color
    ):
        collection = make_collection("Barra da Saia")
        white = make_color("White")
        payload = {
            "name": "White and Green",
            "color_ids": [white["id"]],
            "collection_id": collection["id"],
        }

        assert client.post("/api/color-sets/", json=payload).status_code == 201
        assert client.post("/api/color-sets/", json=payload).status_code == 409

    def test_update_replaces_colours_wholesale(self, client, make_color, make_color_set):
        white = make_color("White")
        green = make_color("Green")
        red = make_color("Red")
        created = make_color_set("White and Green", [white["id"], green["id"]])

        response = client.put(
            f"/api/color-sets/{created['id']}",
            json={"name": "Red only", "color_ids": [red["id"]]},
        )
        assert response.status_code == 200
        assert [c["name"] for c in response.get_json()["colors"]] == ["Red"]

    def test_duplicate_colour_ids_are_collapsed(self, client, make_color):
        white = make_color("White")
        response = client.post(
            "/api/color-sets/",
            json={"name": "Doubled", "color_ids": [white["id"], white["id"]]},
        )
        assert response.status_code == 201
        assert len(response.get_json()["colors"]) == 1

    def test_filter_by_collection(self, client, make_collection, make_color):
        collection = make_collection("Barra da Saia")
        white = make_color("White")
        client.post(
            "/api/color-sets/",
            json={
                "name": "Owned",
                "color_ids": [white["id"]],
                "collection_id": collection["id"],
            },
        )
        client.post(
            "/api/color-sets/", json={"name": "Unowned", "color_ids": [white["id"]]}
        )

        body = client.get(
            f"/api/color-sets/?collection_id={collection['id']}"
        ).get_json()
        assert [s["name"] for s in body["color_sets"]] == ["Owned"]
        assert body["pagination"]["total"] == 1


class TestSizes:
    def test_schema_seeds_s_m_l(self, client):
        body = client.get("/api/sizes/").get_json()
        assert [s["name"] for s in body["sizes"]] == ["S", "M", "L"]

    def test_ordered_by_position_not_name(self, client):
        sizes = client.get("/api/sizes/").get_json()["sizes"]
        assert [s["position"] for s in sizes] == sorted(s["position"] for s in sizes)

    def test_create_new_size(self, client):
        response = client.post("/api/sizes/", json={"name": "XL", "position": 4})
        assert response.status_code == 201
        assert response.get_json()["name"] == "XL"

    def test_duplicate_name_returns_409(self, client):
        assert client.post("/api/sizes/", json={"name": "S"}).status_code == 409

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/sizes/9999").status_code == 404


class TestProductTypes:
    def test_create_top_level_type(self, client):
        response = client.post("/api/product-types/", json={"name": "Hairbrush"})
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Hairbrush"
        assert body["parent_id"] is None
        assert body["sub_types"] == []

    def test_create_sub_type(self, client, make_product_type):
        parent = make_product_type("Coracao")

        response = client.post(
            "/api/product-types/",
            json={"name": "With string", "parent_id": parent["id"]},
        )
        assert response.status_code == 201
        assert response.get_json()["parent_id"] == parent["id"]

    def test_parent_lists_its_sub_types(self, client, make_product_type):
        parent = make_product_type("Coracao")
        make_product_type("With string", parent_id=parent["id"])
        make_product_type("Base for mini figures", parent_id=parent["id"])

        body = client.get(f"/api/product-types/{parent['id']}").get_json()
        assert [s["name"] for s in body["sub_types"]] == [
            "With string",
            "Base for mini figures",
        ]

    def test_sub_type_of_a_sub_type_returns_400(self, client, make_product_type):
        parent = make_product_type("Coracao")
        child = make_product_type("With string", parent_id=parent["id"])

        response = client.post(
            "/api/product-types/", json={"name": "Too deep", "parent_id": child["id"]}
        )
        assert response.status_code == 400

    def test_unknown_parent_returns_404(self, client):
        response = client.post(
            "/api/product-types/", json={"name": "Orphan", "parent_id": 9999}
        )
        assert response.status_code == 404

    def test_same_sub_type_name_allowed_under_different_parents(
        self, client, make_product_type
    ):
        first = make_product_type("Coracao")
        second = make_product_type("Picture frame")

        a = client.post(
            "/api/product-types/", json={"name": "Small", "parent_id": first["id"]}
        )
        b = client.post(
            "/api/product-types/", json={"name": "Small", "parent_id": second["id"]}
        )
        assert a.status_code == 201
        assert b.status_code == 201

    def test_duplicate_sibling_name_returns_409(self, client, make_product_type):
        parent = make_product_type("Coracao")
        make_product_type("With string", parent_id=parent["id"])

        response = client.post(
            "/api/product-types/",
            json={"name": "With string", "parent_id": parent["id"]},
        )
        assert response.status_code == 409

    def test_roots_only_filter(self, client, make_product_type):
        parent = make_product_type("Coracao")
        make_product_type("With string", parent_id=parent["id"])

        body = client.get("/api/product-types/?roots_only=1").get_json()
        assert [t["name"] for t in body["product_types"]] == ["Coracao"]

    def test_parent_id_filter_returns_sub_types(self, client, make_product_type):
        parent = make_product_type("Coracao")
        make_product_type("With string", parent_id=parent["id"])

        body = client.get(f"/api/product-types/?parent_id={parent['id']}").get_json()
        assert [t["name"] for t in body["product_types"]] == ["With string"]

    def test_a_type_cannot_become_its_own_parent(self, client, make_product_type):
        created = make_product_type("Coracao")

        response = client.put(
            f"/api/product-types/{created['id']}",
            json={"name": "Coracao", "parent_id": created["id"]},
        )
        assert response.status_code == 400

    def test_a_type_with_children_cannot_become_a_sub_type(
        self, client, make_product_type
    ):
        parent = make_product_type("Coracao")
        make_product_type("With string", parent_id=parent["id"])
        other = make_product_type("Wooden box")

        response = client.put(
            f"/api/product-types/{parent['id']}",
            json={"name": "Coracao", "parent_id": other["id"]},
        )
        assert response.status_code == 400

    def test_deleting_a_type_cascades_to_sub_types(self, client, make_product_type):
        parent = make_product_type("Coracao")
        child = make_product_type("With string", parent_id=parent["id"])

        client.delete(f"/api/product-types/{parent['id']}")

        assert client.get(f"/api/product-types/{child['id']}").status_code == 404

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0"])
    def test_invalid_pagination_returns_400(self, client, query):
        assert client.get(f"/api/product-types/{query}").status_code == 400
