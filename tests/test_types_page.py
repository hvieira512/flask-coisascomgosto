"""The dashboard's Tipos page, and what a piece is made of.

The page answers two questions the owners actually have: what families the
catalogue is filed under, and what the pieces are made of. Both are counted in
SQL — this page used to fetch every product to count them in the browser, which
the hundred-product page limit would have quietly made wrong.
"""

import json

import pytest


@pytest.fixture()
def signed_in(browser, live_server, make_user):
    make_user("types", password="Passw0rd!")

    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    response = context.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "types", "password": "Passw0rd!"}),
        headers={"Content-Type": "application/json"},
    )
    assert response.ok, response.text()

    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page, errors
    context.close()


@pytest.fixture()
def types_page(signed_in, live_server):
    def _open():
        page, errors = signed_in
        page.goto(f"{live_server}/dashboard/types")
        page.wait_for_selector("#type-rows tr")
        return page, errors

    return _open


class TestTheTypesLedger:
    def test_a_type_shows_its_count_and_a_photograph_of_one_of_its_pieces(
        self, types_page, make_product_type, make_product, client, make_color_set
    ):
        box = make_product_type("Caixa")
        product = make_product("Caixa Redonda", type_id=box["id"])
        color_set = make_color_set("Branco e Dourado")
        variant = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()
        client.post(
            f"/api/products/{product['id']}/images",
            json={"variant_id": variant["id"], "url": "/static/img/caixa.jpg"},
        )

        page, errors = types_page()
        row = page.locator(f'#type-rows tr[data-type-id="{box["id"]}"]')

        assert "1 peça" in row.inner_text()
        assert row.locator("img.dash-thumb").get_attribute("src") == (
            "/static/img/caixa.jpg"
        )
        assert errors == []

    def test_a_type_with_no_photographed_piece_falls_back_to_its_drawing(
        self, types_page, make_product_type, make_product
    ):
        heart = make_product_type("Coracao", icon="fa-heart")
        make_product("Coração de Viana", type_id=heart["id"])

        page, _ = types_page()
        row = page.locator(f'#type-rows tr[data-type-id="{heart["id"]}"]')

        assert row.locator("img.dash-thumb").count() == 0
        assert row.locator(".dash-type-icon .fa-heart").count() >= 1

    def test_the_drawing_column_names_the_icon(
        self, types_page, make_product_type
    ):
        """Named, not only drawn: choosing one is a decision about what the shop
        puts where a photograph is missing, and the name is what the form asks
        for."""
        make_product_type("Caixa", icon="fa-box")

        page, _ = types_page()
        assert "fa-box" in page.locator("#type-rows tr").first.inner_text()

    def test_the_head_counts_types_and_pieces(
        self, types_page, make_product_type, make_product
    ):
        box = make_product_type("Caixa")
        make_product_type("Moldura")
        make_product("Caixa Redonda", type_id=box["id"])
        make_product("Caixa de Joias", type_id=box["id"])

        page, _ = types_page()
        # Three: make_product leans on the shared `product_type` fixture, which is
        # a type of its own with nothing filed under it.
        assert page.locator("#type-count").inner_text() == "3 tipos · 2 peças"

    def test_a_type_with_no_pieces_says_so(self, types_page, make_product_type):
        make_product_type("Tabuleiro")

        page, _ = types_page()
        assert "Sem peças" in page.locator("#type-rows tr").first.inner_text()


class TestTheMaterialsPanel:
    def test_it_counts_the_pieces_made_of_each(
        self, types_page, make_material, make_product
    ):
        wood = make_material("Madeira")
        make_material("Tecido")
        make_product("Caixa", material_ids=[wood["id"]])
        make_product("Moldura", material_ids=[wood["id"]])

        page, errors = types_page()
        panel = page.locator("#material-rows")

        assert "2" in panel.locator("li", has_text="Madeira").inner_text()
        assert "Nenhuma peça" in panel.locator("li", has_text="Tecido").inner_text()
        assert errors == []

    def test_a_piece_of_two_materials_counts_under_both(
        self, types_page, make_material, make_product
    ):
        wood = make_material("Madeira")
        paste = make_material("Pasta de modelar")
        make_product("Manel e Maria", material_ids=[wood["id"], paste["id"]])

        page, _ = types_page()
        panel = page.locator("#material-rows")

        assert "1" in panel.locator("li", has_text="Madeira").inner_text()
        assert "1" in panel.locator("li", has_text="Pasta de modelar").inner_text()


class TestWhatAPieceIsMadeOf:
    """The piece's own form: chips, because a piece may be made of several."""

    @pytest.fixture()
    def products_page(self, signed_in, live_server):
        def _open():
            page, errors = signed_in
            page.goto(f"{live_server}/dashboard/products")
            page.wait_for_selector("#product-list tr[data-product-id]")
            return page, errors

        return _open

    def test_saving_a_piece_of_two_materials_keeps_both(
        self, products_page, make_material, make_product, client
    ):
        wood = make_material("Madeira")
        paste = make_material("Pasta de modelar")
        product = make_product("Manel e Maria", material_ids=[wood["id"]])

        page, errors = products_page()
        page.click(f'#product-list tr[data-product-id="{product["id"]}"]')
        page.wait_for_selector("#pf-materials")

        chips = page.locator("#pf-materials .collection-chip")
        assert chips.count() == 2
        assert (
            page.locator(
                f'#pf-materials [data-material-id="{wood["id"]}"]'
            ).get_attribute("aria-pressed")
            == "true"
        )

        page.click(f'#pf-materials [data-material-id="{paste["id"]}"]')
        page.click("#edit-submit")
        page.wait_for_timeout(800)

        saved = client.get(f"/api/products/{product['id']}").get_json()
        assert [m["name"] for m in saved["materials"]] == [
            "Madeira",
            "Pasta de modelar",
        ]
        assert errors == []

    def test_unpressing_every_chip_leaves_the_piece_unclassified(
        self, products_page, make_material, make_product, client
    ):
        """The list replaces what was there, so "none" has to be sendable."""
        wood = make_material("Madeira")
        product = make_product("Vinho", material_ids=[wood["id"]])

        page, _ = products_page()
        page.click(f'#product-list tr[data-product-id="{product["id"]}"]')
        page.wait_for_selector("#pf-materials")

        page.click(f'#pf-materials [data-material-id="{wood["id"]}"]')
        page.click("#edit-submit")
        page.wait_for_timeout(800)

        assert client.get(f"/api/products/{product['id']}").get_json()["materials"] == []
