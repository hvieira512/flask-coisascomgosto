"""HTTP-level tests for product photographs.

Every photograph belongs to one of the product's colour sets. It used to be able
to belong to the product as a whole instead, standing in for any colour that had
none of its own — which showed a shopper who picked Preto e Branco a photograph
of the white-and-gold piece, and, being preferred by `primary_image`, decided
which tile the catalogue listed. So `variant_id` is required, and these tests are
mostly about that requirement holding at every entry point.
"""

import pytest


@pytest.fixture()
def piece(client, make_color, make_color_set, make_product):
    """A product with one colour, which is the least a photograph needs."""
    white = make_color("White")
    green = make_color("Green")
    color_set = make_color_set("White and Green", [white["id"], green["id"]])
    product = make_product("Caixa Redonda")

    response = client.post(
        f"/api/products/{product['id']}/variants",
        json={"color_set_id": color_set["id"]},
    )
    assert response.status_code == 201, response.get_json()
    return {"product": product, "variant": response.get_json()}


def add_photo(client, piece, url, **extra):
    return client.post(
        f"/api/products/{piece['product']['id']}/images",
        json={"url": url, "variant_id": piece["variant"]["id"], **extra},
    )


class TestAPhotographBelongsToAColour:
    def test_a_product_with_no_photographs_has_no_tile(self, client, make_product):
        product = make_product("Caixa")

        body = client.get(f"/api/products/{product['id']}").get_json()

        assert body["primary_image"] is None
        # The concept is gone from the payload as well as from the table; a
        # client reading product["images"] should fail rather than see [].
        assert "images" not in body

    def test_adding_one_returns_it_with_its_colour(self, client, piece):
        response = add_photo(client, piece, "/static/img/caixa.jpg", alt="Caixa redonda")

        assert response.status_code == 201
        body = response.get_json()
        assert body["url"] == "/static/img/caixa.jpg"
        assert body["variant_id"] == piece["variant"]["id"]

    def test_without_a_colour_it_is_refused(self, client, piece):
        """The whole point of the cutover: there is no product-level photograph
        to create any more."""
        response = client.post(
            f"/api/products/{piece['product']['id']}/images",
            json={"url": "/static/img/caixa.jpg"},
        )

        assert response.status_code == 400

    def test_a_colour_of_another_product_is_refused(self, client, piece, make_product):
        other = make_product("Outra peça")

        response = client.post(
            f"/api/products/{other['id']}/images",
            json={"url": "/x.jpg", "variant_id": piece["variant"]["id"]},
        )

        assert response.status_code == 404

    def test_missing_url_returns_400(self, client, piece):
        response = client.post(
            f"/api/products/{piece['product']['id']}/images",
            json={"variant_id": piece["variant"]["id"]},
        )

        assert response.status_code == 400

    def test_unknown_product_returns_404(self, client):
        assert client.get("/api/products/9999/images").status_code == 404
        assert client.post(
            "/api/products/9999/images", json={"url": "/x.jpg", "variant_id": 1}
        ).status_code == 404


class TestListingThem:
    def test_they_come_back_in_position_order(self, client, piece):
        for url, position in [("/c.jpg", 3), ("/a.jpg", 1), ("/b.jpg", 2)]:
            add_photo(client, piece, url, position=position)

        body = client.get(
            f"/api/products/{piece['product']['id']}/images"
        ).get_json()

        assert [i["url"] for i in body] == ["/a.jpg", "/b.jpg", "/c.jpg"]

    def test_they_appear_on_their_colour(self, client, piece):
        add_photo(client, piece, "/white-green.jpg")

        body = client.get(f"/api/products/{piece['product']['id']}").get_json()

        assert [i["url"] for i in body["variants"][0]["images"]] == ["/white-green.jpg"]

    def test_the_list_can_be_narrowed_to_one_colour(
        self, client, piece, make_color, make_color_set
    ):
        add_photo(client, piece, "/white-green.jpg")

        other_set = make_color_set("Preto e Dourado", [make_color("Preto")["id"]])
        other = client.post(
            f"/api/products/{piece['product']['id']}/variants",
            json={"color_set_id": other_set["id"]},
        ).get_json()
        client.post(
            f"/api/products/{piece['product']['id']}/images",
            json={"url": "/black-gold.jpg", "variant_id": other["id"]},
        )

        body = client.get(
            f"/api/products/{piece['product']['id']}/images"
            f"?variant_id={other['id']}"
        ).get_json()

        assert [i["url"] for i in body] == ["/black-gold.jpg"]


class TestTheTileTheCatalogueShows:
    def test_it_is_the_first_photograph_of_the_first_photographed_colour(
        self, client, piece, make_color, make_color_set
    ):
        """A piece whose first colour has no photograph still gets a tile, from
        whichever colour does — otherwise the catalogue would show a placeholder
        for a piece it has photographs of."""
        bare_set = make_color_set("Sem fotografia", [make_color("Cinza")["id"]])
        bare = client.post(
            f"/api/products/{piece['product']['id']}/variants",
            json={"color_set_id": bare_set["id"]},
        ).get_json()
        assert bare["id"]

        add_photo(client, piece, "/first.jpg", position=1)
        add_photo(client, piece, "/second.jpg", position=2)

        body = client.get(f"/api/products/{piece['product']['id']}").get_json()

        assert body["primary_image"]["url"] == "/first.jpg"


class TestChangingAndRemoving:
    def test_update_keeps_the_colour_requirement(self, client, piece):
        created = add_photo(client, piece, "/old.jpg").get_json()

        response = client.put(
            f"/api/products/{piece['product']['id']}/images/{created['id']}",
            json={"url": "/new.jpg", "alt": "novo"},
        )

        assert response.status_code == 400

    def test_update_changes_the_url(self, client, piece):
        created = add_photo(client, piece, "/old.jpg").get_json()

        response = client.put(
            f"/api/products/{piece['product']['id']}/images/{created['id']}",
            json={
                "url": "/new.jpg",
                "alt": "novo",
                "variant_id": piece["variant"]["id"],
            },
        )

        assert response.status_code == 200
        assert response.get_json()["url"] == "/new.jpg"

    def test_delete_removes_it(self, client, piece):
        created = add_photo(client, piece, "/x.jpg").get_json()

        response = client.delete(
            f"/api/products/{piece['product']['id']}/images/{created['id']}"
        )

        assert response.status_code == 200
        assert client.get(
            f"/api/products/{piece['product']['id']}/images"
        ).get_json() == []

    def test_another_products_photograph_is_out_of_reach(
        self, client, piece, make_product
    ):
        second = make_product("Segunda")
        image = add_photo(client, piece, "/x.jpg").get_json()

        response = client.delete(f"/api/products/{second['id']}/images/{image['id']}")

        assert response.status_code == 404

    def test_deleting_the_product_removes_its_photographs(self, client, piece):
        add_photo(client, piece, "/x.jpg")

        client.delete(f"/api/products/{piece['product']['id']}")

        assert client.get(
            f"/api/products/{piece['product']['id']}/images"
        ).status_code == 404

    def test_deleting_the_colour_removes_its_photographs(self, client, piece):
        """There is nowhere for them to go: a photograph with no colour is the
        state this cutover removed."""
        photo = add_photo(client, piece, "/x.jpg").get_json()

        client.delete(
            f"/api/products/{piece['product']['id']}"
            f"/variants/{piece['variant']['id']}"
        )

        body = client.get(f"/api/products/{piece['product']['id']}/images").get_json()
        assert [i["id"] for i in body] == []
        assert photo["id"]
