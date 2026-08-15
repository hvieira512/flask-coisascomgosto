"""HTTP-level tests for how products compose the catalog layers: types,
collections, colour-set variants and sizes.

The worked example throughout is a "Caixa Redonda" in the Barra da Saia
collection, offered in four colour sets.
"""

import pytest


@pytest.fixture()
def round_box(client, make_collection, make_color, make_color_set, make_product):
    """A product with four colour-set variants, as described in the domain."""
    collection = make_collection("Barra da Saia")

    colors = {
        name: make_color(name)["id"]
        for name in ["White", "Green", "Red", "Blue", "Gray"]
    }
    pairs = [
        ("White and Green", ["White", "Green"]),
        ("Red and White", ["Red", "White"]),
        ("Blue and White", ["Blue", "White"]),
        ("White and Gray", ["White", "Gray"]),
    ]
    color_sets = [
        make_color_set(
            name, [colors[c] for c in members], collection_id=collection["id"]
        )
        for name, members in pairs
    ]

    product = make_product("Caixa Redonda", collection_id=collection["id"])
    for color_set in color_sets:
        response = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        )
        assert response.status_code == 201, response.get_json()

    return {
        "product": product,
        "collection": collection,
        "color_sets": color_sets,
        "colors": colors,
    }


class TestProductType:
    def test_product_carries_its_type(self, client, make_product, make_product_type):
        product_type = make_product_type("Hairbrush")
        product = make_product("Escova", type_id=product_type["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["name"] == "Hairbrush"
        assert body["type"]["parent"] is None

    def test_sub_type_exposes_its_parent(
        self, client, make_product, make_product_type
    ):
        parent = make_product_type("Coracao")
        sub = make_product_type("With string", parent_id=parent["id"])
        product = make_product("Coracao pendurado", type_id=sub["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["name"] == "With string"
        assert body["type"]["parent"]["name"] == "Coracao"

    def test_type_is_optional(self, client, make_product):
        product = make_product("Sem tipo")
        assert client.get(f"/api/products/{product['id']}").get_json()["type"] is None

    def test_unknown_type_returns_404(self, client, make_category):
        category = make_category("Madeira")
        response = client.post(
            "/api/products/",
            json={
                "name": "Ghost",
                "description": "d",
                "category_id": category["id"],
                "type_id": 9999,
            },
        )
        assert response.status_code == 404

    def test_filter_by_type(self, client, make_product, make_product_type):
        brush = make_product_type("Hairbrush")
        frame = make_product_type("Picture frame")
        make_product("Escova", type_id=brush["id"])
        make_product("Moldura", type_id=frame["id"])

        body = client.get(f"/api/products/?type_id={brush['id']}").get_json()
        assert [p["name"] for p in body["products"]] == ["Escova"]

    def test_filtering_by_parent_type_includes_sub_typed_products(
        self, client, make_product, make_product_type
    ):
        parent = make_product_type("Coracao")
        with_string = make_product_type("With string", parent_id=parent["id"])
        base = make_product_type("Base for mini figures", parent_id=parent["id"])
        make_product("Pendurado", type_id=with_string["id"])
        make_product("Base", type_id=base["id"])
        make_product("Escova")  # untyped, must not appear

        body = client.get(f"/api/products/?type_id={parent['id']}").get_json()
        assert sorted(p["name"] for p in body["products"]) == ["Base", "Pendurado"]
        assert body["pagination"]["total"] == 2

    def test_deleting_a_type_clears_it_on_products(
        self, client, make_product, make_product_type
    ):
        product_type = make_product_type("Hairbrush")
        product = make_product("Escova", type_id=product_type["id"])

        client.delete(f"/api/product-types/{product_type['id']}")

        assert client.get(f"/api/products/{product['id']}").get_json()["type"] is None


class TestProductVariants:
    def test_product_lists_all_four_variants(self, client, round_box):
        product_id = round_box["product"]["id"]

        body = client.get(f"/api/products/{product_id}").get_json()
        assert [v["color_set"]["name"] for v in body["variants"]] == [
            "White and Green",
            "Red and White",
            "Blue and White",
            "White and Gray",
        ]

    def test_variant_nests_its_colours_in_order(self, client, round_box):
        product_id = round_box["product"]["id"]

        variants = client.get(f"/api/products/{product_id}/variants").get_json()[
            "variants"
        ]
        first = next(v for v in variants if v["color_set"]["name"] == "White and Green")
        assert [c["name"] for c in first["color_set"]["colors"]] == ["White", "Green"]

    def test_variant_nests_the_collection(self, client, round_box):
        product_id = round_box["product"]["id"]

        variants = client.get(f"/api/products/{product_id}/variants").get_json()[
            "variants"
        ]
        assert variants[0]["color_set"]["collection"]["name"] == "Barra da Saia"

    def test_same_colour_set_twice_returns_409(self, client, round_box):
        product_id = round_box["product"]["id"]
        color_set_id = round_box["color_sets"][0]["id"]

        response = client.post(
            f"/api/products/{product_id}/variants", json={"color_set_id": color_set_id}
        )
        assert response.status_code == 409

    def test_unknown_colour_set_returns_404(self, client, make_product):
        product = make_product("Caixa")
        response = client.post(
            f"/api/products/{product['id']}/variants", json={"color_set_id": 9999}
        )
        assert response.status_code == 404

    def test_unknown_product_returns_404(self, client, make_color_set):
        color_set = make_color_set("White and Green")
        assert client.get("/api/products/9999/variants").status_code == 404
        assert (
            client.post(
                "/api/products/9999/variants", json={"color_set_id": color_set["id"]}
            ).status_code
            == 404
        )

    def test_delete_removes_only_that_variant(self, client, round_box):
        product_id = round_box["product"]["id"]
        variants = client.get(f"/api/products/{product_id}/variants").get_json()[
            "variants"
        ]

        response = client.delete(
            f"/api/products/{product_id}/variants/{variants[0]['id']}"
        )
        assert response.status_code == 200

        remaining = client.get(f"/api/products/{product_id}/variants").get_json()[
            "variants"
        ]
        assert len(remaining) == 3

    def test_cannot_delete_a_variant_of_another_product(
        self, client, round_box, make_product
    ):
        other = make_product("Outra caixa")
        variants = client.get(
            f"/api/products/{round_box['product']['id']}/variants"
        ).get_json()["variants"]

        response = client.delete(
            f"/api/products/{other['id']}/variants/{variants[0]['id']}"
        )
        assert response.status_code == 404

    def test_deleting_a_colour_set_removes_the_variant(self, client, round_box):
        product_id = round_box["product"]["id"]
        color_set_id = round_box["color_sets"][0]["id"]

        client.delete(f"/api/color-sets/{color_set_id}")

        body = client.get(f"/api/products/{product_id}").get_json()
        assert len(body["variants"]) == 3

    def test_deleting_the_product_removes_its_variants(self, client, round_box):
        product_id = round_box["product"]["id"]
        client.delete(f"/api/products/{product_id}")

        assert client.get(f"/api/products/{product_id}/variants").status_code == 404


class TestProductSizes:
    def test_default_size_can_be_set(self, client, make_product, sizes):
        product = make_product("Caixa", default_size_id=sizes["M"]["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["default_size"]["name"] == "M"

    def test_default_size_is_optional(self, client, make_product):
        product = make_product("Caixa")
        assert (
            client.get(f"/api/products/{product['id']}").get_json()["default_size"]
            is None
        )

    def test_unknown_default_size_returns_404(self, client, make_category):
        category = make_category("Madeira")
        response = client.post(
            "/api/products/",
            json={
                "name": "Ghost",
                "description": "d",
                "category_id": category["id"],
                "default_size_id": 9999,
            },
        )
        assert response.status_code == 404

    def test_product_starts_with_no_sizes(self, client, make_product):
        product = make_product("Caixa")
        assert client.get(f"/api/products/{product['id']}/sizes").get_json() == []

    def test_sizes_can_be_assigned(self, client, make_product, sizes):
        product = make_product("Caixa")

        response = client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["S"]["id"], sizes["M"]["id"], sizes["L"]["id"]]},
        )
        assert response.status_code == 200
        assert [s["name"] for s in response.get_json()] == ["S", "M", "L"]

    def test_sizes_come_back_in_display_order(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["L"]["id"], sizes["S"]["id"]]},
        )

        body = client.get(f"/api/products/{product['id']}/sizes").get_json()
        assert [s["name"] for s in body] == ["S", "L"]

    def test_sizes_appear_on_the_product(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["S"]["id"], sizes["M"]["id"]]},
        )

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert [s["name"] for s in body["sizes"]] == ["S", "M"]

    def test_put_replaces_rather_than_appends(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["S"]["id"], sizes["M"]["id"]]},
        )

        response = client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": [sizes["L"]["id"]]}
        )
        assert [s["name"] for s in response.get_json()] == ["L"]

    def test_empty_list_clears_sizes(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": [sizes["S"]["id"]]}
        )

        response = client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": []}
        )
        assert response.get_json() == []

    def test_unknown_size_returns_404(self, client, make_product):
        product = make_product("Caixa")
        response = client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": [9999]}
        )
        assert response.status_code == 404

    def test_unknown_product_returns_404(self, client, sizes):
        assert client.get("/api/products/9999/sizes").status_code == 404
        assert (
            client.put(
                "/api/products/9999/sizes", json={"size_ids": [sizes["S"]["id"]]}
            ).status_code
            == 404
        )

    def test_deleting_a_size_detaches_it_from_products(
        self, client, make_product, sizes
    ):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["S"]["id"], sizes["M"]["id"]]},
        )

        client.delete(f"/api/sizes/{sizes['S']['id']}")

        body = client.get(f"/api/products/{product['id']}/sizes").get_json()
        assert [s["name"] for s in body] == ["M"]

    def test_deleting_the_default_size_clears_it(self, client, make_product, sizes):
        product = make_product("Caixa", default_size_id=sizes["M"]["id"])

        client.delete(f"/api/sizes/{sizes['M']['id']}")

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["default_size"] is None


class TestProductCollection:
    def test_product_carries_its_collection(self, client, round_box):
        product_id = round_box["product"]["id"]

        body = client.get(f"/api/products/{product_id}").get_json()
        assert body["collection"]["name"] == "Barra da Saia"

    def test_unknown_collection_returns_404(self, client, make_category):
        category = make_category("Madeira")
        response = client.post(
            "/api/products/",
            json={
                "name": "Ghost",
                "description": "d",
                "category_id": category["id"],
                "collection_id": 9999,
            },
        )
        assert response.status_code == 404

    def test_filter_by_collection(self, client, round_box, make_product):
        make_product("Fora da coleccao")
        collection_id = round_box["collection"]["id"]

        body = client.get(f"/api/products/?collection_id={collection_id}").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa Redonda"]
        assert body["pagination"]["total"] == 1

    def test_filter_by_category(self, client, make_category, make_product):
        madeira = make_category("Madeira")
        tecido = make_category("Tecido")
        make_product("Caixa", category_id=madeira["id"])
        make_product("Lenco", category_id=tecido["id"])

        body = client.get(f"/api/products/?category_id={madeira['id']}").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa"]

    def test_search_matches_type_name(
        self, client, make_product, make_product_type
    ):
        brush = make_product_type("Hairbrush")
        make_product("Escova", type_id=brush["id"])
        make_product("Moldura")

        body = client.get("/api/products/?q=Hairbrush").get_json()
        assert [p["name"] for p in body["products"]] == ["Escova"]

    def test_list_resolves_variants_for_every_row(
        self, client, round_box, make_product
    ):
        make_product("Sem variantes")

        body = client.get("/api/products/").get_json()
        by_name = {p["name"]: p for p in body["products"]}
        assert len(by_name["Caixa Redonda"]["variants"]) == 4
        assert by_name["Sem variantes"]["variants"] == []
