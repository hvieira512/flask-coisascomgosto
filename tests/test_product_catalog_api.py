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
            name, [colors[c] for c in members], collection_ids=[collection["id"]]
        )
        for name, members in pairs
    ]

    product = make_product("Caixa Redonda")
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
        assert body["type"] == {
            "id": product_type["id"],
            "name": "Hairbrush",
            # Resolved, not passed through: "Hairbrush" matches the brush keyword.
            "icon": "fa-brush",
        }

    def test_type_is_required(self, client, make_material):
        """Every piece is something; there is no untyped state."""
        material = make_material("Madeira")
        response = client.post(
            "/api/products/",
            json={"name": "Sem tipo", "description": "d",
                  "material_ids": [material["id"]]},
        )
        assert response.status_code == 400

    def test_unknown_type_returns_404(self, client, make_material):
        material = make_material("Madeira")
        response = client.post(
            "/api/products/",
            json={
                "name": "Ghost",
                "description": "d",
                "material_ids": [material["id"]],
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

    def test_filtering_by_type_returns_every_piece_of_that_family(
        self, client, make_product, make_product_type
    ):
        """A family holds the pieces directly — "Caixa" is the type, and
        "Caixa rectangular" is one of its pieces."""
        box = make_product_type("Caixa")
        make_product("Caixa rectangular", type_id=box["id"])
        make_product("Caixa de Joias", type_id=box["id"])
        make_product("Escova")  # the shared default type, must not appear

        body = client.get(f"/api/products/?type_id={box['id']}").get_json()
        assert sorted(p["name"] for p in body["products"]) == [
            "Caixa de Joias",
            "Caixa rectangular",
        ]
        assert body["pagination"]["total"] == 2

    def test_deleting_a_type_still_in_use_returns_409(
        self, client, make_product, make_product_type
    ):
        """type_id is NOT NULL, so there is no unfiled state to move the piece
        into — refusing beats destroying it."""
        brush = make_product_type("Hairbrush")
        product = make_product("Escova", type_id=brush["id"])

        response = client.delete(f"/api/product-types/{brush['id']}")
        assert response.status_code == 409
        assert "1 product" in response.get_json()["message"]

        # Both survive.
        assert client.get(f"/api/product-types/{brush['id']}").status_code == 200
        assert client.get(f"/api/products/{product['id']}").status_code == 200

    def test_deleting_an_unused_type_succeeds(self, client, make_product_type):
        spare = make_product_type("Tabuleiro")
        assert client.delete(f"/api/product-types/{spare['id']}").status_code == 200
        assert client.get(f"/api/product-types/{spare['id']}").status_code == 404


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

    def test_variant_names_its_colour_set_and_nothing_about_collections(
        self, client, round_box
    ):
        """A colour set may be gathered by several collections, and a variant has
        never had a use for them — the storefront filters by the *product's*
        collection. Carrying the list through every variant of every product would
        be a join per page for a field nobody reads."""
        product_id = round_box["product"]["id"]

        variants = client.get(f"/api/products/{product_id}/variants").get_json()[
            "variants"
        ]

        assert variants[0]["color_set"]["name"] == "White and Green"
        assert "collection" not in variants[0]["color_set"]
        assert "collections" not in variants[0]["color_set"]

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
        product = make_product("Caixa", default_size_id=sizes["Médio"]["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["default_size"]["name"] == "Médio"

    def test_default_size_is_optional(self, client, make_product):
        product = make_product("Caixa")
        assert (
            client.get(f"/api/products/{product['id']}").get_json()["default_size"]
            is None
        )

    def test_unknown_default_size_returns_404(self, client, product_type, make_material):
        material = make_material("Madeira")
        response = client.post(
            "/api/products/",
            json={
                "name": "Ghost",
                "description": "d",
                "type_id": product_type["id"],
                "material_ids": [material["id"]],
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
            json={"size_ids": [sizes["Pequeno"]["id"], sizes["Médio"]["id"], sizes["Grande"]["id"]]},
        )
        assert response.status_code == 200
        assert [s["name"] for s in response.get_json()] == ["Pequeno", "Médio", "Grande"]

    def test_sizes_come_back_in_display_order(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["Grande"]["id"], sizes["Pequeno"]["id"]]},
        )

        body = client.get(f"/api/products/{product['id']}/sizes").get_json()
        assert [s["name"] for s in body] == ["Pequeno", "Grande"]

    def test_sizes_appear_on_the_product(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["Pequeno"]["id"], sizes["Médio"]["id"]]},
        )

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert [s["name"] for s in body["sizes"]] == ["Pequeno", "Médio"]

    def test_put_replaces_rather_than_appends(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["Pequeno"]["id"], sizes["Médio"]["id"]]},
        )

        response = client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": [sizes["Grande"]["id"]]}
        )
        assert [s["name"] for s in response.get_json()] == ["Grande"]

    def test_empty_list_clears_sizes(self, client, make_product, sizes):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes", json={"size_ids": [sizes["Pequeno"]["id"]]}
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
                "/api/products/9999/sizes", json={"size_ids": [sizes["Pequeno"]["id"]]}
            ).status_code
            == 404
        )

    def test_deleting_a_size_detaches_it_from_products(
        self, client, make_product, sizes
    ):
        product = make_product("Caixa")
        client.put(
            f"/api/products/{product['id']}/sizes",
            json={"size_ids": [sizes["Pequeno"]["id"], sizes["Médio"]["id"]]},
        )

        client.delete(f"/api/sizes/{sizes['Pequeno']['id']}")

        body = client.get(f"/api/products/{product['id']}/sizes").get_json()
        assert [s["name"] for s in body] == ["Médio"]

    def test_deleting_the_default_size_clears_it(self, client, make_product, sizes):
        product = make_product("Caixa", default_size_id=sizes["Médio"]["id"])

        client.delete(f"/api/sizes/{sizes['Médio']['id']}")

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["default_size"] is None


class TestProductCollection:
    """A piece is in a collection because one of its colourways is. All four of the
    round box's colour sets are gathered by Barra da Saia, and it is in it once."""

    def test_product_carries_the_collections_its_colours_are_in(
        self, client, round_box
    ):
        product_id = round_box["product"]["id"]

        body = client.get(f"/api/products/{product_id}").get_json()
        assert [c["name"] for c in body["collections"]] == ["Barra da Saia"]

    def test_a_piece_whose_colours_are_in_none_is_in_none(
        self, client, make_product, make_color, make_color_set
    ):
        product = make_product("Sem colecção")
        color_set = make_color_set("Cor solta", [make_color("Tom")["id"]])
        client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        )

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["collections"] == []

    def test_a_collection_sent_with_a_piece_changes_nothing(
        self, client, product_type, make_collection
    ):
        """flask-restx validates the fields a model declares and passes over the
        rest, so an old client still sending collection_id is not refused — it is
        simply not listened to, and the piece is in whatever its colours say. Worth
        pinning: the alternative reading is that the field still works."""
        collection = make_collection("Filigrana")
        response = client.post(
            "/api/products/",
            json={"name": "Ghost", "description": "d",
                  "type_id": product_type["id"], "collection_id": collection["id"]},
        )
        assert response.status_code == 201
        assert response.get_json()["collections"] == []

    def test_filter_by_collection(self, client, round_box, make_product):
        make_product("Fora da coleccao")
        collection_id = round_box["collection"]["id"]

        body = client.get(f"/api/products/?collection_id={collection_id}").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa Redonda"]
        assert body["pagination"]["total"] == 1

    def test_filter_by_material(self, client, make_material, make_product):
        madeira = make_material("Madeira")
        tecido = make_material("Tecido")
        make_product("Caixa", material_ids=[madeira["id"]])
        make_product("Lenco", material_ids=[tecido["id"]])

        body = client.get(f"/api/products/?material_id={madeira['id']}").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa"]

    def test_a_piece_of_two_materials_is_found_under_either(
        self, client, make_material, make_product
    ):
        """And exactly once: matching the join with a JOIN would return it twice."""
        madeira = make_material("Madeira")
        pasta = make_material("Pasta de modelar")
        make_product("Manel e Maria", material_ids=[madeira["id"], pasta["id"]])

        for material in (madeira, pasta):
            body = client.get(f"/api/products/?material_id={material['id']}").get_json()
            assert [p["name"] for p in body["products"]] == ["Manel e Maria"]
            assert body["pagination"]["total"] == 1

        both = client.get(
            f"/api/products/?material_id={madeira['id']}&material_id={pasta['id']}"
        ).get_json()
        assert [p["name"] for p in both["products"]] == ["Manel e Maria"]

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


class TestTypeDeletionGuard:
    """type_id is NOT NULL, so a type in use cannot be removed."""

    def test_message_names_the_number_of_products(
        self, client, make_product, make_product_type
    ):
        brush = make_product_type("Escova de cabelo")
        make_product("Escova A", type_id=brush["id"])
        make_product("Escova B", type_id=brush["id"])

        body = client.delete(f"/api/product-types/{brush['id']}").get_json()
        assert "2 products still use" in body["message"]

