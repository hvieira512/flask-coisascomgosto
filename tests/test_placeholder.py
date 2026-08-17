"""Tests for the no-photo product placeholder.

The tile borrows the product's own identity: a pale wash of its first variant
colour with its product-type icon. It is rendered by static/js/store/placeholder.js;
the icon-guessing half is shared with the server through the `type_icon` filter,
which is what these tests cover.
"""


class TestProductTypeIcon:
    def test_icon_round_trips(self, client, auth_client):
        response = client.post(
            "/api/product-types/", json={"name": "Coração", "icon": "fa-heart"}
        )
        assert response.status_code == 201
        assert response.get_json()["icon"] == "fa-heart"

    def test_icon_is_optional(self, client, make_product_type):
        assert make_product_type("Sem ícone")["icon"] is None

    def test_icon_can_be_updated(self, client, make_product_type):
        created = make_product_type("Moldura")

        response = client.put(
            f"/api/product-types/{created['id']}",
            json={"name": "Moldura", "icon": "fa-image"},
        )
        assert response.get_json()["icon"] == "fa-image"

    def test_product_exposes_its_type_icon(self, client, make_product):
        product_type = client.post(
            "/api/product-types/", json={"name": "Caixa", "icon": "fa-box"}
        ).get_json()
        product = make_product("Caixa Redonda", type_id=product_type["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["icon"] == "fa-box"

    def test_sub_type_inherits_the_parent_icon(self, client, make_product):
        """A sub-type with no icon of its own falls back to its parent's."""
        parent = client.post(
            "/api/product-types/", json={"name": "Coração", "icon": "fa-heart"}
        ).get_json()
        sub = client.post(
            "/api/product-types/",
            json={"name": "Com fio", "parent_id": parent["id"]},
        ).get_json()
        assert sub["icon"] is None

        product = make_product("Coração de Viana", type_id=sub["id"])
        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["icon"] == "fa-heart"

    def test_sub_type_icon_wins_over_the_parent(self, client, make_product):
        parent = client.post(
            "/api/product-types/", json={"name": "Caixa", "icon": "fa-box"}
        ).get_json()
        sub = client.post(
            "/api/product-types/",
            json={"name": "Redonda", "parent_id": parent["id"], "icon": "fa-circle-dot"},
        ).get_json()

        product = make_product("Caixa Redonda", type_id=sub["id"])
        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["icon"] == "fa-circle-dot"


class TestTypeIconFilter:
    """The `type_icon` Jinja filter — the single source of the keyword table.

    It used to be duplicated inline in a Jinja macro; the macro rendered the
    landing page's featured products and went away with that section, so the
    logic now lives in one place and is used by the product-types grid.
    static/js/store/placeholder.js carries the same table for client-rendered
    tiles.
    """

    def _icon(self, app, product_type):
        return app.jinja_env.filters["type_icon"](product_type)

    def test_explicit_icon_wins(self, app):
        assert self._icon(app, {"name": "Caixa", "icon": "fa-star"}) == "fa-star"

    def test_guesses_from_the_name(self, app):
        assert self._icon(app, {"name": "Coração de Viana"}) == "fa-heart"
        assert self._icon(app, {"name": "Moldura pequena"}) == "fa-image"
        assert self._icon(app, {"name": "Caixa"}) == "fa-box"

    def test_guess_is_accent_and_case_insensitive(self, app):
        assert self._icon(app, {"name": "CORACAO"}) == "fa-heart"

    def test_falls_back_to_the_parent_name(self, app):
        sub = {"name": "Com fio", "parent": {"name": "Coração"}}
        assert self._icon(app, sub) == "fa-heart"

    def test_unknown_name_gets_the_default(self, app):
        assert self._icon(app, {"name": "Qualquer coisa"}) == "fa-gift"

    def test_missing_type_gets_the_default(self, app):
        assert self._icon(app, None) == "fa-gift"


class TestProductTypeGridIcons:
    """The landing page draws each type with its icon."""

    def test_type_card_renders_its_icon(self, client, make_product_type):
        make_product_type("Moldura", icon="fa-image")

        html = client.get("/").get_data(as_text=True)
        assert "type-card-icon" in html
        assert "fa-image" in html

    def test_type_without_an_icon_falls_back_to_the_guess(self, client,
                                                          make_product_type):
        make_product_type("Coração de Viana")

        html = client.get("/").get_data(as_text=True)
        assert "fa-heart" in html


class TestPlaceholderScriptIsLoaded:
    def test_storefront_loads_it_before_the_page_modules(self, client):
        html = client.get("/products").get_data(as_text=True)
        assert html.index("js/store/placeholder.js") < html.index("js/store/products.js")

    def test_dashboard_loads_it(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})

        html = client.get("/dashboard/products").get_data(as_text=True)
        assert "js/store/placeholder.js" in html


def test_placeholder_tile_keeps_its_load_bearing_rules():
    """The tile is styled entirely in CSS, so losing these leaves a valid page
    rendering a bare icon in a corner — which no other test would notice. A
    comment-stripping regex deleted exactly this block once.

    Only the two declarations that fail silently are pinned: without the flex
    centring the icon sits top-left, and without container-type the circle's cqw
    width resolves against the viewport instead of the tile.
    """
    import pathlib

    css = pathlib.Path("static/css/store.css").read_text()
    block = css.split(".product-placeholder {")[1].split("}")[0]

    assert "display: flex" in block
    assert "align-items: center" in block
    assert "justify-content: center" in block
    assert "container-type: inline-size" in block
