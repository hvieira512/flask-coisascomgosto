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

    def test_a_product_always_gets_a_resolved_icon(self, client, make_product):
        """Guessed from the name when the type carries none, so the browser has
        nothing left to work out — placeholder.js used to hold a second copy of
        the keyword table for exactly this."""
        product_type = client.post(
            "/api/product-types/", json={"name": "Coração"}
        ).get_json()
        assert product_type["icon"] is None

        product = make_product("Coração de Viana", type_id=product_type["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["icon"] == "fa-heart"

    def test_an_unrecognisable_name_gets_the_default(self, client, make_product):
        product_type = client.post(
            "/api/product-types/", json={"name": "Qualquer coisa"}
        ).get_json()
        product = make_product("Uma peça", type_id=product_type["id"])

        body = client.get(f"/api/products/{product['id']}").get_json()
        assert body["type"]["icon"] == "fa-gift"

    def test_the_types_endpoint_keeps_the_icon_unresolved(self, client, make_product_type):
        """The dashboard's form offers "Adivinhar pelo nome" for a type with no
        icon, which it can only do while null still means null. Resolving it here
        too would quietly turn a guess into a saved choice."""
        created = make_product_type("Coração")

        body = client.get(f"/api/product-types/{created['id']}").get_json()
        assert body["icon"] is None


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


class TestPlaceholderIsImported:
    """The tile used to be a global published by a classic script the page had to
    load first. It is a module export now, so the guarantee is an import in
    whoever draws a tile — order in the HTML no longer decides anything."""

    @staticmethod
    def _source(path):
        import pathlib as _p

        return _p.Path(path).read_text(encoding="utf-8")

    def test_every_drawer_of_a_tile_imports_it(self):
        for path in [
            "static/js/store/products.js",     # the catalogue grid
            "static/js/store/gallery.js",      # the product page's stage
            "static/js/dashboard/products/fetch.js",   # the dashboard's rows
        ]:
            assert 'import { ProductPlaceholder }' in self._source(path), path

    def test_it_is_no_longer_a_script_tag(self, client, make_user):
        """A page that loaded it for its side effect would still work, and would
        hide the missing import until something else broke."""
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})

        for page in ["/products", "/dashboard/products"]:
            html = client.get(page).get_data(as_text=True)
            assert "js/store/placeholder.js" not in html, page


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
