"""HTTP-level tests for /api/products."""

import pytest


class TestListProducts:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/products/").get_json()
        assert body["products"] == []
        assert body["pagination"]["total"] == 0

    def test_product_is_returned_with_nested_materials(self, client, make_material, make_product):
        material = make_material("Madeira")
        make_product("Vinho", material_ids=[material["id"]])

        product = client.get("/api/products/").get_json()["products"][0]
        assert product["name"] == "Vinho"
        assert product["materials"] == [{"id": material["id"], "name": "Madeira"}]

    def test_a_piece_can_be_made_of_several(self, client, make_material, make_product):
        """Manel e Maria: a wooden base and a figure of modelling paste."""
        wood = make_material("Madeira")
        paste = make_material("Pasta de modelar")
        make_product("Manel e Maria", material_ids=[wood["id"], paste["id"]])

        product = client.get("/api/products/").get_json()["products"][0]
        assert [m["name"] for m in product["materials"]] == [
            "Madeira",
            "Pasta de modelar",
        ]

    def test_a_piece_nobody_classified_has_none(self, client, make_product):
        make_product("Vinho")
        assert client.get("/api/products/").get_json()["products"][0]["materials"] == []

    def test_search_matches_product_name(self, client, make_product):
        make_product("Vinho")
        make_product("Cerveja")

        body = client.get("/api/products/?q=Vin").get_json()
        assert [p["name"] for p in body["products"]] == ["Vinho"]

    def test_search_matches_the_type_name(self, client, make_product_type, make_product):
        """Search covers the product and its type. Material is descriptive and
        deliberately not searchable — a shopper looks for a heart, not for wood."""
        heart = make_product_type("Coracao de Viana")
        box = make_product_type("Caixa")
        make_product("Vinho", type_id=heart["id"])
        make_product("Bolo", type_id=box["id"])

        body = client.get("/api/products/?q=Caix").get_json()
        assert [p["name"] for p in body["products"]] == ["Bolo"]

    def test_search_does_not_500_on_the_joined_query(self, client, make_product):
        """Regression: an unqualified `name` was ambiguous across the join."""
        make_product("Vinho")

        assert client.get("/api/products/?q=Vinho").status_code == 200

    def test_search_total_reflects_filter(self, client, make_product):
        make_product("Vinho")
        make_product("Cerveja")

        assert client.get("/api/products/?q=Vin").get_json()["pagination"]["total"] == 1

    def test_pagination_splits_results(self, client, make_material, make_product):
        material = make_material("Madeira")
        for name in ["A", "B", "C"]:
            make_product(name, material_ids=[material["id"]])

        body = client.get("/api/products/?page=2&limit=2").get_json()
        assert [p["name"] for p in body["products"]] == ["C"]
        assert body["pagination"] == {"total": 3, "page": 2, "pages": 2, "limit": 2}

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0", "?page=0"])
    def test_invalid_pagination_returns_400(self, client, product_type, query):
        assert client.get(f"/api/products/{query}").status_code == 400

    def test_default_order_is_insertion_order(self, client, make_product):
        """What the dashboard wants: an unphotographed piece stays where the
        owners left it, so it is findable."""
        make_product("Sem fotografia")
        photographed = make_product("Com fotografia")
        client.post(
            f"/api/products/{photographed['id']}/images", json={"url": "/a.jpg"}
        )

        body = client.get("/api/products/").get_json()
        assert [p["name"] for p in body["products"]] == [
            "Sem fotografia",
            "Com fotografia",
        ]

    def test_photographed_first_puts_pieces_with_photographs_ahead(
        self, client, make_product, make_color, make_color_set
    ):
        """What the storefront wants: nobody should have to page past pieces
        with nothing to look at."""
        make_product("Sem fotografia")
        photographed = make_product("Com fotografia")

        color_set = make_color_set("Branco", [make_color("Branco")["id"]])
        variant = client.post(
            f"/api/products/{photographed['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()
        client.post(
            f"/api/products/{photographed['id']}/images",
            json={"url": "/a.jpg", "variant_id": variant["id"]},
        )

        body = client.get("/api/products/?photographed_first=1").get_json()
        assert [p["name"] for p in body["products"]] == [
            "Com fotografia",
            "Sem fotografia",
        ]

    def test_several_type_ids_read_as_or(self, client, make_product, make_product_type):
        """A shopper ticking Caixa and Moldura wants both families."""
        box = make_product_type("Caixa")
        frame = make_product_type("Moldura")
        make_product("Caixa de Joias", type_id=box["id"])
        make_product("Moldura Oval", type_id=frame["id"])
        make_product("Outra coisa")

        body = client.get(
            f"/api/products/?type_id={box['id']}&type_id={frame['id']}"
        ).get_json()
        assert sorted(p["name"] for p in body["products"]) == [
            "Caixa de Joias",
            "Moldura Oval",
        ]
        assert body["pagination"]["total"] == 2

    def test_a_single_type_id_still_works(self, client, make_product, make_product_type):
        """The dashboard and every shared link send one value."""
        box = make_product_type("Caixa")
        make_product("Caixa de Joias", type_id=box["id"])
        make_product("Outra coisa")

        body = client.get(f"/api/products/?type_id={box['id']}").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa de Joias"]

    def test_different_filters_still_narrow_with_and(
        self, client, make_product, make_product_type, make_collection,
        put_in_collection,
    ):
        """OR inside a filter, AND between them."""
        box = make_product_type("Caixa")
        frame = make_product_type("Moldura")
        filigrana = make_collection("Filigrana")
        piece = make_product("Caixa Filigrana", type_id=box["id"])
        put_in_collection(piece, filigrana)
        make_product("Moldura sem colecção", type_id=frame["id"])

        body = client.get(
            f"/api/products/?type_id={box['id']}&type_id={frame['id']}"
            f"&collection_id={filigrana['id']}"
        ).get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa Filigrana"]

    def test_photographed_first_still_paginates(self, client, make_product):
        """The reorder must not double-count or drop rows: total is unchanged."""
        make_product("A")
        make_product("B")

        body = client.get("/api/products/?photographed_first=1&limit=1").get_json()
        assert body["pagination"]["total"] == 2
        assert len(body["products"]) == 1


class TestCreateProduct:
    def test_creates_and_returns_product(self, client, product_type, make_material):
        material = make_material("Madeira")

        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Tinto", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
        )
        assert response.status_code == 201

        body = response.get_json()
        assert body["name"] == "Vinho"
        assert body["description"] == "Tinto"
        assert [m["name"] for m in body["materials"]] == ["Madeira"]

    def test_unknown_material_returns_404(self, client, product_type):
        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Tinto", "type_id": product_type["id"],
                  "material_ids": [9999]},
        )
        assert response.status_code == 404

    def test_one_unknown_material_refuses_the_whole_list(
        self, client, product_type, make_material
    ):
        """Half-applied would be worse: the piece would be saved made of only the
        material that happened to exist."""
        material = make_material("Madeira")
        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Tinto", "type_id": product_type["id"],
                  "material_ids": [material["id"], 9999]},
        )
        assert response.status_code == 404
        assert client.get("/api/products/").get_json()["products"] == []

    def test_duplicate_name_returns_409(self, client, product_type, make_material, make_product):
        material = make_material("Madeira")
        make_product("Vinho", material_ids=[material["id"]])

        response = client.post(
            "/api/products/",
            json={"name": "Vinho", "description": "Outro", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
        )
        assert response.status_code == 409

    @pytest.mark.parametrize(
        "payload",
        [
            {"description": "Tinto", "material_ids": [1]},
            {"name": "Vinho", "material_ids": [1]},
            {"name": "Vinho", "description": "Tinto"},
            {},
        ],
    )
    def test_missing_fields_return_400(self, client, make_material, payload):
        make_material("Madeira")
        assert client.post("/api/products/", json=payload).status_code == 400


class TestGetProduct:
    def test_returns_existing_product(self, client, make_product):
        created = make_product("Vinho")

        body = client.get(f"/api/products/{created['id']}").get_json()
        assert body["name"] == "Vinho"

    def test_unknown_id_returns_404(self, client, product_type):
        assert client.get("/api/products/9999").status_code == 404


class TestUpdateProduct:
    def test_updates_all_fields(self, client, product_type, make_material, make_product):
        created = make_product("Vinho")
        other = make_material("Tecido")

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Bolo", "description": "Doce", "type_id": product_type["id"],
                  "material_ids": [other["id"]]},
        )
        assert response.status_code == 200

        body = response.get_json()
        assert body["name"] == "Bolo"
        assert body["description"] == "Doce"
        assert [m["name"] for m in body["materials"]] == ["Tecido"]

    def test_the_materials_sent_replace_the_ones_before(
        self, client, product_type, make_material, make_product
    ):
        wood = make_material("Madeira")
        paste = make_material("Pasta de modelar")
        created = make_product("Manel e Maria", material_ids=[wood["id"], paste["id"]])

        body = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Manel e Maria", "description": "d",
                  "type_id": product_type["id"], "material_ids": [paste["id"]]},
        ).get_json()
        assert [m["name"] for m in body["materials"]] == ["Pasta de modelar"]

    def test_sending_none_leaves_the_piece_unclassified(
        self, client, product_type, make_material, make_product
    ):
        wood = make_material("Madeira")
        created = make_product("Vinho", material_ids=[wood["id"]])

        body = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Vinho", "description": "d", "type_id": product_type["id"],
                  "material_ids": []},
        ).get_json()
        assert body["materials"] == []

    def test_unknown_product_returns_404(self, client, product_type, make_material):
        material = make_material("Madeira")

        response = client.put(
            "/api/products/9999",
            json={"name": "Ghost", "description": "d", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
        )
        assert response.status_code == 404

    def test_unknown_product_does_not_return_a_null_body(self, client, product_type, make_material):
        """Regression: a missing product used to marshal to 200 with all-null fields."""
        material = make_material("Madeira")

        response = client.put(
            "/api/products/9999",
            json={"name": "Ghost", "description": "d", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
        )
        assert response.get_json().get("id") is None
        assert response.status_code != 200

    def test_unknown_material_returns_404(self, client, product_type, make_product):
        created = make_product("Vinho")

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Vinho", "description": "d", "type_id": product_type["id"],
                  "material_ids": [9999]},
        )
        assert response.status_code == 404

    def test_name_taken_by_another_returns_409(self, client, product_type, make_material, make_product):
        material = make_material("Madeira")
        make_product("Vinho", material_ids=[material["id"]])
        other = make_product("Cerveja", material_ids=[material["id"]])

        response = client.put(
            f"/api/products/{other['id']}",
            json={"name": "Vinho", "description": "d", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
        )
        assert response.status_code == 409

    def test_keeping_own_name_is_allowed(self, client, product_type, make_material, make_product):
        material = make_material("Madeira")
        created = make_product("Vinho", material_ids=[material["id"]])

        response = client.put(
            f"/api/products/{created['id']}",
            json={"name": "Vinho", "description": "novo", "type_id": product_type["id"],
                  "material_ids": [material["id"]]},
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

    def test_404_message_names_the_product_not_a_material(self, client):
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

    def test_type_filter_narrows_to_that_family(self, client, make_product,
                                                make_product_type):
        box = make_product_type("Caixa")
        make_product("Caixa Redonda Filigrana", type_id=box["id"])
        make_product("Outra")

        body = client.get(
            f"/api/products/?type_id={box['id']}&limit=100").get_json()
        assert [p["name"] for p in body["products"]] == ["Caixa Redonda Filigrana"]

    def test_collection_filter_narrows(
        self, client, make_product, make_collection, put_in_collection
    ):
        collection = make_collection("Bordados")
        put_in_collection(make_product("Bastidor"), collection)
        make_product("Sem colecção")

        body = client.get(
            f"/api/products/?collection_id={collection['id']}&limit=100").get_json()
        assert [p["name"] for p in body["products"]] == ["Bastidor"]

    def test_filters_combine(
        self, client, make_product, make_collection, put_in_collection
    ):
        collection = make_collection("Bordados")
        put_in_collection(make_product("Bastidor Bordado"), collection)
        put_in_collection(make_product("Bastidor Viana"), collection)

        body = client.get(
            f"/api/products/?collection_id={collection['id']}&q=viana&limit=100"
        ).get_json()
        assert [p["name"] for p in body["products"]] == ["Bastidor Viana"]

    def test_no_match_is_an_empty_page_not_an_error(self, client, make_product):
        make_product("Caixa")

        response = client.get("/api/products/?q=zzzz&limit=100")
        assert response.status_code == 200
        assert response.get_json()["products"] == []


class TestProductFacets:
    """Per-option counts for the catalogue sidebar."""

    def test_counts_products_per_type(self, client, make_product, make_product_type):
        box = make_product_type("Caixa")
        frame = make_product_type("Moldura")
        make_product("Caixa de Joias", type_id=box["id"])
        make_product("Caixa de Garrafa", type_id=box["id"])
        make_product("Moldura Oval", type_id=frame["id"])

        facets = client.get("/api/products/facets").get_json()
        counts = {row["id"]: row["count"] for row in facets["types"]}
        assert counts[box["id"]] == 2
        assert counts[frame["id"]] == 1

    def test_an_option_with_no_products_is_absent(self, client, make_product_type):
        """The sidebar reads a missing id as zero and greys the entry out."""
        spare = make_product_type("Tabuleiro")

        facets = client.get("/api/products/facets").get_json()
        assert spare["id"] not in {row["id"] for row in facets["types"]}

    def test_collections_and_materials_are_counted_too(
        self, client, make_product, make_collection, make_material, put_in_collection
    ):
        collection = make_collection("Filigrana")
        material = make_material("Madeira")
        put_in_collection(
            make_product("Caixa", material_ids=[material["id"]]), collection
        )

        facets = client.get("/api/products/facets").get_json()
        assert {row["id"]: row["count"] for row in facets["collections"]} == {
            collection["id"]: 1
        }
        assert {row["id"]: row["count"] for row in facets["materials"]} == {
            material["id"]: 1
        }

    def test_a_piece_of_two_materials_counts_under_both(
        self, client, make_product, make_material
    ):
        """So the counts can add up to more than the catalogue holds, which is the
        true answer to "how many pieces are made of wood"."""
        wood = make_material("Madeira")
        paste = make_material("Pasta de modelar")
        make_product("Manel e Maria", material_ids=[wood["id"], paste["id"]])

        facets = client.get("/api/products/facets").get_json()
        assert {row["id"]: row["count"] for row in facets["materials"]} == {
            wood["id"]: 1,
            paste["id"]: 1,
        }

    def test_facets_are_public(self, anon_client):
        """The storefront reads them with no session and no token."""
        assert anon_client.get("/api/products/facets").status_code == 200
