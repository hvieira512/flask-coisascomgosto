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
        """Its own folder is what makes replacing one safe to delete."""
        collection = make_collection("Filigrana")
        self._upload(client, collection["id"])

        assert not (cover_dir / "products").exists()

    def test_replacing_a_cover_removes_the_file_it_replaced(
        self, client, make_collection, cover_dir
    ):
        collection = make_collection("Filigrana")
        first = self._upload(client, collection["id"]).get_json()["image_url"]
        second = self._upload(client, collection["id"], "outra.jpg").get_json()["image_url"]

        assert first != second
        assert not (cover_dir / "collections" / pathlib.Path(first).name).exists()
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

    def test_removing_the_cover_clears_the_column_and_the_file(
        self, client, make_collection, cover_dir
    ):
        collection = make_collection("Filigrana")
        url = self._upload(client, collection["id"]).get_json()["image_url"]

        response = client.delete(f"/api/collections/{collection['id']}/cover")
        assert response.status_code == 200
        assert response.get_json()["image_url"] is None
        assert not (cover_dir / "collections" / pathlib.Path(url).name).exists()

    def test_deleting_the_collection_takes_its_cover_with_it(
        self, client, make_collection, cover_dir
    ):
        collection = make_collection("Filigrana")
        url = self._upload(client, collection["id"]).get_json()["image_url"]

        client.delete(f"/api/collections/{collection['id']}")
        assert not (cover_dir / "collections" / pathlib.Path(url).name).exists()

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
