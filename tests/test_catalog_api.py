"""HTTP-level tests for the catalog layers: collections, colours, colour sets,
sizes and product types."""

import io
import pathlib

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


class TestWhichColourSetsACollectionGathers:
    """A collection gathers colour sets, and the owners edit that from the
    collection.

    A link, not a move: a set may be gathered by several collections at once —
    the same two colours are the same combination wherever they appear — so
    listing one here does not take it from anywhere.
    """

    @pytest.fixture()
    def sets(self, make_color, make_color_set):
        white = make_color("Branco", hex="#FFFFFF")
        return {
            "gold": make_color_set("Branco e Dourado", color_ids=[white["id"]]),
            "black": make_color_set("Preto e Branco", color_ids=[white["id"]]),
            "blue": make_color_set("Azul e Branco", color_ids=[white["id"]]),
        }

    def _put(self, client, collection_id, ids):
        return client.put(
            f"/api/collections/{collection_id}/color-sets",
            json={"color_set_ids": ids},
        )

    def test_a_new_collection_owns_none(self, client, make_collection):
        collection = make_collection("Filigrana")
        body = client.get(f"/api/collections/{collection['id']}/color-sets").get_json()
        assert body == []

    def test_they_can_be_assigned(self, client, make_collection, sets):
        collection = make_collection("Filigrana")
        response = self._put(
            client, collection["id"], [sets["gold"]["id"], sets["black"]["id"]]
        )

        assert response.status_code == 200
        assert sorted(s["name"] for s in response.get_json()) == [
            "Branco e Dourado", "Preto e Branco"
        ]

    def test_the_colour_set_now_names_the_collection(
        self, client, make_collection, sets
    ):
        collection = make_collection("Filigrana")
        self._put(client, collection["id"], [sets["gold"]["id"]])

        body = client.get(f"/api/color-sets/{sets['gold']['id']}").get_json()
        assert [c["name"] for c in body["collections"]] == ["Filigrana"]

    def test_leaving_one_out_takes_it_out(self, client, make_collection, sets):
        collection = make_collection("Filigrana")
        self._put(client, collection["id"], [sets["gold"]["id"], sets["black"]["id"]])
        self._put(client, collection["id"], [sets["gold"]["id"]])

        remaining = client.get(
            f"/api/collections/{collection['id']}/color-sets"
        ).get_json()
        assert [s["name"] for s in remaining] == ["Branco e Dourado"]

        # Dropped from the collection rather than deleted.
        dropped = client.get(f"/api/color-sets/{sets['black']['id']}").get_json()
        assert dropped["collections"] == []

    def test_an_empty_list_empties_the_collection(self, client, make_collection, sets):
        collection = make_collection("Filigrana")
        self._put(client, collection["id"], [sets["gold"]["id"]])

        assert self._put(client, collection["id"], []).get_json() == []

    def test_gathering_one_that_another_collection_has_keeps_both(
        self, client, make_collection, sets
    ):
        """The whole point of the join: "Branco e Dourado" is Filigrana's *and*
        Bordados', without being created twice."""
        bordados = make_collection("Bordados")
        filigrana = make_collection("Filigrana")
        self._put(client, bordados["id"], [sets["gold"]["id"]])

        self._put(client, filigrana["id"], [sets["gold"]["id"]])

        for collection in (bordados, filigrana):
            assert [
                s["name"]
                for s in client.get(
                    f"/api/collections/{collection['id']}/color-sets"
                ).get_json()
            ] == ["Branco e Dourado"], collection["name"]

        both = client.get(f"/api/color-sets/{sets['gold']['id']}").get_json()
        assert sorted(c["name"] for c in both["collections"]) == [
            "Bordados", "Filigrana"
        ]

    def test_it_does_not_disturb_the_other_collections(
        self, client, make_collection, sets
    ):
        bordados = make_collection("Bordados")
        filigrana = make_collection("Filigrana")
        self._put(client, bordados["id"], [sets["black"]["id"]])

        self._put(client, filigrana["id"], [sets["gold"]["id"]])

        assert [
            s["name"]
            for s in client.get(
                f"/api/collections/{bordados['id']}/color-sets"
            ).get_json()
        ] == ["Preto e Branco"]

    def test_an_unknown_colour_set_is_404_and_changes_nothing(
        self, client, make_collection, sets
    ):
        collection = make_collection("Filigrana")
        self._put(client, collection["id"], [sets["gold"]["id"]])

        response = self._put(client, collection["id"], [9999])
        assert response.status_code == 404
        assert [
            s["name"]
            for s in client.get(
                f"/api/collections/{collection['id']}/color-sets"
            ).get_json()
        ] == ["Branco e Dourado"], "a rejected write must not have emptied it"

    def test_an_unknown_collection_is_404(self, client, sets):
        assert self._put(client, 9999, [sets["gold"]["id"]]).status_code == 404
        assert client.get("/api/collections/9999/color-sets").status_code == 404

    def test_it_needs_a_token(self, anon_client, client, make_collection, sets):
        collection = make_collection("Filigrana")
        response = anon_client.put(
            f"/api/collections/{collection['id']}/color-sets",
            json={"color_set_ids": [sets["gold"]["id"]]},
        )
        assert response.status_code == 401

    def test_reading_them_does_not(self, anon_client, client, make_collection):
        """The storefront reads collections without signing in."""
        collection = make_collection("Filigrana")
        assert anon_client.get(
            f"/api/collections/{collection['id']}/color-sets"
        ).status_code == 200


class TestCollectionCover:
    """The photograph that stands for a collection on the catalogue.

    Chosen rather than derived from the pieces, because which photograph speaks
    for a collection is an editorial decision, and a derived one would change
    under the owners whenever a row moved.
    """

    @pytest.fixture(autouse=True)
    def cover_dir(self, tmp_path, monkeypatch):
        """Covers land somewhere disposable, and in their own folder."""
        import uploads

        monkeypatch.setattr(uploads, "COLLECTION_DIR", tmp_path / "collections")
        monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path / "products")
        return tmp_path

    def _upload(self, client, collection_id, name="capa.jpg"):
        from tests.test_uploads import image_bytes

        return client.post(
            f"/api/collections/{collection_id}/cover",
            data={"file": (io.BytesIO(image_bytes()), name)},
            content_type="multipart/form-data",
        )

    def test_a_new_collection_has_no_cover(self, client, make_collection):
        assert make_collection("Filigrana")["image_url"] is None

    def test_it_can_be_set_as_a_plain_url(self, client):
        """A path placed by hand still works, the way product images do."""
        response = client.post(
            "/api/collections/",
            json={"name": "Filigrana", "image_url": "/static/img/logo.png"},
        )
        assert response.get_json()["image_url"] == "/static/img/logo.png"

    def test_uploading_stores_it_and_points_the_collection_at_it(
        self, client, make_collection, cover_dir
    ):
        collection = make_collection("Filigrana")
        response = self._upload(client, collection["id"])
        assert response.status_code == 201

        url = response.get_json()["image_url"]
        assert url.startswith("/static/img/collections/")
        assert (cover_dir / "collections" / pathlib.Path(url).name).is_file()

    def test_a_cover_is_not_stored_with_the_pieces(
        self, client, make_collection, cover_dir
    ):
        """Its own folder is what lets the sweep tell a cover nobody uses any more
        from a photograph a product row still points at."""
        collection = make_collection("Filigrana")
        self._upload(client, collection["id"])

        assert not (cover_dir / "products").exists()

    def test_replacing_a_cover_keeps_the_file_it_replaced(
        self, client, make_collection, cover_dir
    ):
        """It used to be unlinked here. Nothing in the application deletes a file
        now — `flask sweep-uploads` collects it once nothing points at it, so
        changing your mind twice costs nothing."""
        collection = make_collection("Filigrana")
        first = self._upload(client, collection["id"]).get_json()["image_url"]
        second = self._upload(client, collection["id"], "outra.jpg").get_json()["image_url"]

        assert first != second
        assert (cover_dir / "collections" / pathlib.Path(first).name).is_file()
        assert (cover_dir / "collections" / pathlib.Path(second).name).is_file()

    def test_replacing_a_cover_that_points_at_a_product_photo_keeps_the_photo(
        self, client, make_collection, cover_dir
    ):
        """The reason covers have a folder of their own. Set a cover to one of the
        pieces' photographs, change your mind, and the piece must still have it."""
        piece_photo = cover_dir / "products" / "caixa-abcd1234.jpg"
        piece_photo.parent.mkdir(parents=True, exist_ok=True)
        piece_photo.write_bytes(b"a real photograph as far as this test cares")

        collection = make_collection("Filigrana")
        client.put(
            f"/api/collections/{collection['id']}",
            json={"name": "Filigrana", "image_url": f"/static/img/products/{piece_photo.name}"},
        )
        self._upload(client, collection["id"])

        assert piece_photo.is_file(), "a collection cover deleted a piece's photograph"

    def test_removing_the_cover_clears_the_column_and_keeps_the_file(
        self, client, make_collection, cover_dir
    ):
        collection = make_collection("Filigrana")
        url = self._upload(client, collection["id"]).get_json()["image_url"]

        response = client.delete(f"/api/collections/{collection['id']}/cover")

        assert response.status_code == 200
        assert response.get_json()["image_url"] is None
        assert (cover_dir / "collections" / pathlib.Path(url).name).is_file()

    def test_deleting_the_collection_keeps_its_cover_on_disk(
        self, client, make_collection, cover_dir
    ):
        """The row goes; the photograph waits for the sweep."""
        collection = make_collection("Filigrana")
        url = self._upload(client, collection["id"]).get_json()["image_url"]

        client.delete(f"/api/collections/{collection['id']}")

        assert (cover_dir / "collections" / pathlib.Path(url).name).is_file()

    def test_a_file_that_is_not_an_image_is_refused(self, client, make_collection):
        collection = make_collection("Filigrana")
        response = client.post(
            f"/api/collections/{collection['id']}/cover",
            data={"file": (io.BytesIO(b"\xff\xd8\xff\xe0 nope"), "capa.jpg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_uploading_requires_a_token(self, anon_client, client, make_collection):
        collection = make_collection("Filigrana")
        response = anon_client.post(
            f"/api/collections/{collection['id']}/cover",
            data={"file": (io.BytesIO(b"x"), "capa.jpg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 401

    def test_unknown_collection_is_404(self, client):
        assert self._upload(client, 9999).status_code == 404
        assert client.delete("/api/collections/9999/cover").status_code == 404


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

    def test_a_set_can_be_in_no_collection(self, client, make_color):
        white = make_color("White")
        response = client.post(
            "/api/color-sets/", json={"name": "Just White", "color_ids": [white["id"]]}
        )
        assert response.status_code == 201
        assert response.get_json()["collections"] == []

    def test_nests_its_collections(self, client, make_collection, make_color):
        collection = make_collection("Barra da Saia")
        white = make_color("White")

        response = client.post(
            "/api/color-sets/",
            json={
                "name": "White",
                "color_ids": [white["id"]],
                "collection_ids": [collection["id"]],
            },
        )
        assert [
            c["name"] for c in response.get_json()["collections"]
        ] == ["Barra da Saia"]

    def test_unknown_colour_returns_404(self, client):
        response = client.post(
            "/api/color-sets/", json={"name": "Ghost", "color_ids": [9999]}
        )
        assert response.status_code == 404

    def test_unknown_collection_returns_404(self, client, make_color):
        white = make_color("White")
        response = client.post(
            "/api/color-sets/",
            json={"name": "X", "color_ids": [white["id"]], "collection_ids": [9999]},
        )
        assert response.status_code == 404

    def test_one_set_can_be_in_several_collections(
        self, client, make_collection, make_color
    ):
        """Which is why the name is not scoped to a collection: it is one set."""
        first = make_collection("First")
        second = make_collection("Second")
        white = make_color("White")

        response = client.post(
            "/api/color-sets/",
            json={
                "name": "White and Green",
                "color_ids": [white["id"]],
                "collection_ids": [first["id"], second["id"]],
            },
        )

        assert response.status_code == 201
        assert sorted(
            c["name"] for c in response.get_json()["collections"]
        ) == ["First", "Second"]

    def test_the_name_is_taken_across_the_catalogue(
        self, client, make_collection, make_color
    ):
        """Two collections each having their own "White and Green" was the old
        shape, and it is what made the same combination exist twice."""
        first = make_collection("First")
        second = make_collection("Second")
        white = make_color("White")
        payload = {"name": "White and Green", "color_ids": [white["id"]]}

        assert client.post(
            "/api/color-sets/", json={**payload, "collection_ids": [first["id"]]}
        ).status_code == 201
        assert client.post(
            "/api/color-sets/", json={**payload, "collection_ids": [second["id"]]}
        ).status_code == 409

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
                "collection_ids": [collection["id"]],
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
    def test_schema_seeds_the_three_sizes(self, client):
        body = client.get("/api/sizes/").get_json()
        assert [s["name"] for s in body["sizes"]] == ["Pequeno", "Médio", "Grande"]

    def test_ordered_by_position_not_name(self, client):
        sizes = client.get("/api/sizes/").get_json()["sizes"]
        assert [s["position"] for s in sizes] == sorted(s["position"] for s in sizes)

    def test_create_new_size(self, client):
        response = client.post("/api/sizes/", json={"name": "Extra grande", "position": 4})
        assert response.status_code == 201
        assert response.get_json()["name"] == "Extra grande"

    def test_duplicate_name_returns_409(self, client):
        assert client.post("/api/sizes/", json={"name": "Pequeno"}).status_code == 409

    def test_an_accented_name_round_trips(self, client):
        """utf8mb4 all the way through: "Médio" is seeded, read and matched with
        its accent intact."""
        body = client.get("/api/sizes/").get_json()
        medium = next(s for s in body["sizes"] if s["position"] == 2)

        assert medium["name"] == "Médio"
        assert client.get(f"/api/sizes/{medium['id']}").get_json()["name"] == "Médio"

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/sizes/9999").status_code == 404


class TestProductTypes:
    """Types are flat: the family is the type, the shape is the piece's name."""

    def test_create_a_type(self, client):
        response = client.post("/api/product-types/", json={"name": "Caixa"})
        assert response.status_code == 201
        assert response.get_json()["name"] == "Caixa"

    def test_a_type_has_no_hierarchy_fields(self, client, make_product_type):
        """Nothing nests. A parent_id would be a level the owners do not use."""
        body = client.get(
            f"/api/product-types/{make_product_type('Caixa')['id']}"
        ).get_json()

        assert "parent_id" not in body
        assert "sub_types" not in body

    def test_parent_id_in_the_payload_is_ignored(self, client, make_product_type):
        """The field is gone from the model, so flask-restx drops it rather than
        quietly storing a relationship the schema no longer has."""
        parent = make_product_type("Caixa")

        response = client.post(
            "/api/product-types/",
            json={"name": "Caixa redonda", "parent_id": parent["id"]},
        )
        assert response.status_code == 201
        assert "parent_id" not in response.get_json()

    def test_duplicate_name_returns_409(self, client, make_product_type):
        make_product_type("Caixa")

        response = client.post("/api/product-types/", json={"name": "Caixa"})
        assert response.status_code == 409

    def test_rename_keeps_the_name_unique(self, client, make_product_type):
        make_product_type("Caixa")
        other = make_product_type("Moldura")

        response = client.put(
            f"/api/product-types/{other['id']}", json={"name": "Caixa"}
        )
        assert response.status_code == 409

    def test_search_matches_the_name(self, client, make_product_type):
        make_product_type("Caixa")
        make_product_type("Moldura")

        body = client.get("/api/product-types/?q=Mold").get_json()
        assert [t["name"] for t in body["product_types"]] == ["Moldura"]

    def test_delete_removes_the_type(self, client, make_product_type):
        created = make_product_type("Caixa")

        assert client.delete(f"/api/product-types/{created['id']}").status_code == 200
        assert client.get(f"/api/product-types/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/product-types/9999").status_code == 404

    @pytest.mark.parametrize("query", ["?page=abc", "?limit=0"])
    def test_invalid_pagination_returns_400(self, client, query):
        assert client.get(f"/api/product-types/{query}").status_code == 400
