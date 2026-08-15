"""HTTP-level tests for product images and the variant -> product fallback."""

import pytest


@pytest.fixture()
def product_with_variant(client, make_color, make_color_set, make_product):
    """A product carrying one colour-set variant."""
    white = make_color("White")
    green = make_color("Green")
    color_set = make_color_set("White and Green", [white["id"], green["id"]])
    product = make_product("Caixa Redonda")

    response = client.post(
        f"/api/products/{product['id']}/variants",
        json={"color_set_id": color_set["id"]},
    )
    assert response.status_code == 201
    return {"product": product, "variant": response.get_json()}


class TestProductImages:
    def test_product_starts_with_no_images(self, client, make_product):
        product = make_product("Caixa")

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["images"] == []
        assert body["primary_image"] is None

    def test_add_product_level_image(self, client, make_product):
        product = make_product("Caixa")

        response = client.post(
            f"/api/products/{product['id']}/images",
            json={"url": "/static/img/caixa.jpg", "alt": "Caixa redonda"},
        )
        assert response.status_code == 201

        body = response.get_json()
        assert body["url"] == "/static/img/caixa.jpg"
        assert body["variant_id"] is None

    def test_images_come_back_in_position_order(self, client, make_product):
        product = make_product("Caixa")
        for url, position in [("/c.jpg", 3), ("/a.jpg", 1), ("/b.jpg", 2)]:
            client.post(
                f"/api/products/{product['id']}/images",
                json={"url": url, "position": position},
            )

        body = client.get(f"/api/products/{product['id']}/images").get_json()
        assert [i["url"] for i in body] == ["/a.jpg", "/b.jpg", "/c.jpg"]

    def test_primary_image_is_the_first_product_image(self, client, make_product):
        product = make_product("Caixa")
        client.post(
            f"/api/products/{product['id']}/images",
            json={"url": "/first.jpg", "position": 1},
        )
        client.post(
            f"/api/products/{product['id']}/images",
            json={"url": "/second.jpg", "position": 2},
        )

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["primary_image"]["url"] == "/first.jpg"

    def test_update_an_image(self, client, make_product):
        product = make_product("Caixa")
        created = client.post(
            f"/api/products/{product['id']}/images", json={"url": "/old.jpg"}
        ).get_json()

        response = client.put(
            f"/api/products/{product['id']}/images/{created['id']}",
            json={"url": "/new.jpg", "alt": "novo"},
        )
        assert response.status_code == 200
        assert response.get_json()["url"] == "/new.jpg"

    def test_delete_an_image(self, client, make_product):
        product = make_product("Caixa")
        created = client.post(
            f"/api/products/{product['id']}/images", json={"url": "/x.jpg"}
        ).get_json()

        assert (
            client.delete(
                f"/api/products/{product['id']}/images/{created['id']}"
            ).status_code
            == 200
        )
        assert client.get(f"/api/products/{product['id']}/images").get_json() == []

    def test_unknown_product_returns_404(self, client):
        assert client.get("/api/products/9999/images").status_code == 404
        assert (
            client.post("/api/products/9999/images", json={"url": "/x.jpg"}).status_code
            == 404
        )

    def test_missing_url_returns_400(self, client, make_product):
        product = make_product("Caixa")
        assert (
            client.post(f"/api/products/{product['id']}/images", json={}).status_code
            == 400
        )

    def test_cannot_touch_another_products_image(self, client, make_product):
        first = make_product("Primeira")
        second = make_product("Segunda")
        image = client.post(
            f"/api/products/{first['id']}/images", json={"url": "/x.jpg"}
        ).get_json()

        assert (
            client.delete(
                f"/api/products/{second['id']}/images/{image['id']}"
            ).status_code
            == 404
        )

    def test_deleting_a_product_removes_its_images(self, client, make_product):
        product = make_product("Caixa")
        client.post(f"/api/products/{product['id']}/images", json={"url": "/x.jpg"})

        client.delete(f"/api/products/{product['id']}")

        assert client.get(f"/api/products/{product['id']}/images").status_code == 404


class TestVariantImages:
    def test_attach_an_image_to_a_variant(self, client, product_with_variant):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]

        response = client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/white-green.jpg", "variant_id": variant_id},
        )
        assert response.status_code == 201
        assert response.get_json()["variant_id"] == variant_id

    def test_variant_images_appear_on_the_variant(self, client, product_with_variant):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/white-green.jpg", "variant_id": variant_id},
        )

        body = client.get(f"/api/products/{product_id}").get_json()
        assert [i["url"] for i in body["variants"][0]["images"]] == ["/white-green.jpg"]

    def test_variant_images_are_excluded_from_product_level_images(
        self, client, product_with_variant
    ):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/variant.jpg", "variant_id": variant_id},
        )
        client.post(f"/api/products/{product_id}/images", json={"url": "/product.jpg"})

        body = client.get(f"/api/products/{product_id}").get_json()
        assert [i["url"] for i in body["images"]] == ["/product.jpg"]

    def test_primary_image_falls_back_to_a_variant_photo(
        self, client, product_with_variant
    ):
        """A product photographed only per colour set still gets a grid tile."""
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/only-variant.jpg", "variant_id": variant_id},
        )

        body = client.get(f"/api/products/{product_id}").get_json()
        assert body["images"] == []
        assert body["primary_image"]["url"] == "/only-variant.jpg"

    def test_product_level_image_wins_over_variant_for_primary(
        self, client, product_with_variant
    ):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/variant.jpg", "variant_id": variant_id},
        )
        client.post(f"/api/products/{product_id}/images", json={"url": "/product.jpg"})

        body = client.get(f"/api/products/{product_id}").get_json()
        assert body["primary_image"]["url"] == "/product.jpg"

    def test_filter_images_by_variant(self, client, product_with_variant):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/variant.jpg", "variant_id": variant_id},
        )
        client.post(f"/api/products/{product_id}/images", json={"url": "/product.jpg"})

        body = client.get(
            f"/api/products/{product_id}/images?variant_id={variant_id}"
        ).get_json()
        assert [i["url"] for i in body] == ["/variant.jpg"]

    def test_variant_of_another_product_returns_404(
        self, client, product_with_variant, make_product
    ):
        other = make_product("Outra")
        variant_id = product_with_variant["variant"]["id"]

        response = client.post(
            f"/api/products/{other['id']}/images",
            json={"url": "/x.jpg", "variant_id": variant_id},
        )
        assert response.status_code == 404

    def test_deleting_a_variant_removes_its_images(self, client, product_with_variant):
        product_id = product_with_variant["product"]["id"]
        variant_id = product_with_variant["variant"]["id"]
        client.post(
            f"/api/products/{product_id}/images",
            json={"url": "/variant.jpg", "variant_id": variant_id},
        )

        client.delete(f"/api/products/{product_id}/variants/{variant_id}")

        assert client.get(f"/api/products/{product_id}/images").get_json() == []


class TestStorefrontPages:
    def test_catalog_page_renders(self, client):
        response = client.get("/products")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert 'id="product-grid"' in html
        assert 'id="active-filters"' in html
        assert "bulma.min.css" in html

    def test_product_page_renders_with_its_id(self, client, make_product):
        product = make_product("Caixa")

        response = client.get(f"/products/{product['id']}")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert f'data-product-id="{product["id"]}"' in html
        assert 'id="thumb-rail"' in html
        assert 'id="gallery-stage"' in html
