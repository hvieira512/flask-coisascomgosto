"""The product page's gallery, in a real browser.

A colour may have several photographs and a piece has its own, and none of them were
visible: the thumbnails lived in a 72px rail beside the stage that hid itself unless
the chosen colour had two or more, and a piece's own photographs were not shown at
all once a colour was chosen.

`live_server` and `browser` come from conftest.py.
"""

import io

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def piece(client, make_product, make_color, make_color_set):
    """A piece with two colours — one photographed twice, one not at all — and a
    photograph of its own.

    That is the shape the catalogue actually has: most colours carry one photograph
    and most pieces carry one of their own.
    """
    from tests.test_uploads import image_bytes

    product = make_product("Coração de Mesa")
    white = make_color("Branco", hex="#FFFFFF")
    gold = make_color("Dourado", hex="#C8A24B")
    photographed = make_color_set("Branco e Dourado", color_ids=[white["id"], gold["id"]])
    bare = make_color_set("Preto e Branco", color_ids=[white["id"]])

    variants = {}
    for name, color_set in (("photographed", photographed), ("bare", bare)):
        variants[name] = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()

    def upload(**form):
        response = client.post(
            f"/api/products/{product['id']}/images/upload",
            data={"file": (io.BytesIO(image_bytes()), "foto.jpg"), **form},
            content_type="multipart/form-data",
        )
        assert response.status_code == 201, response.get_json()

    upload(variant_id=str(variants["photographed"]["id"]))
    upload(variant_id=str(variants["photographed"]["id"]))
    upload()   # the piece's own

    return product


@pytest.fixture()
def page(browser, live_server, piece):
    context = browser.new_context(viewport={"width": 1280, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.goto(f"{live_server}/products/{piece['id']}")
    page.wait_for_selector("#thumb-strip .strip-thumb")
    yield page, errors
    context.close()


def labels(page):
    return [t.strip() for t in page.locator(".strip-label").all_text_contents()]


class TestTheStrip:
    def test_it_shows_every_photograph_the_visitor_can_reach(self, page):
        """Two of the chosen colour, one of the piece."""
        view, errors = page
        assert view.locator(".strip-thumb").count() == 3
        assert errors == []

    def test_the_strip_is_below_the_stage(self, page):
        view, _ = page
        stage = view.locator("#gallery-stage").bounding_box()
        strip = view.locator("#thumb-strip").bounding_box()

        assert strip["y"] > stage["y"] + stage["height"] - 2
        assert abs(strip["x"] - stage["x"]) < 2, "the strip is not aligned with it"

    def test_the_stage_gets_the_whole_column(self, page):
        """The rail used to take 72px of it at every width."""
        view, _ = page
        fills = view.locator("#gallery-stage").evaluate(
            """el => {
                // Against the column's content box: Bulma pads a .column by .75rem,
                // which the stage sits inside rather than covering.
                const column = el.closest('.column');
                const style = getComputedStyle(column);
                const inner = column.clientWidth
                    - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
                return el.getBoundingClientRect().width >= inner - 1;
            }"""
        )
        assert fills, "something other than the photograph is taking the column's width"

    def test_the_two_sources_are_labelled(self, page):
        """A photograph of the piece must not pass for one of the chosen colour."""
        view, _ = page
        assert labels(view) == ["ESTA COR", "DA PEÇA"] or labels(view) == [
            "Esta cor", "Da peça"
        ]

    def test_clicking_a_thumbnail_changes_the_photograph(self, page):
        view, _ = page
        before = view.locator("#stage-image").get_attribute("src")

        view.locator(".strip-thumb").nth(1).click()
        view.wait_for_function(
            """(previous) => document.getElementById('stage-image').src !== previous""",
            arg=before,
        )
        assert "2 / 3" in view.locator("#stage-counter").inner_text()

    def test_the_active_thumbnail_is_marked(self, page):
        view, _ = page
        assert "is-active" in view.locator(".strip-thumb").first.get_attribute("class")

        view.locator(".strip-thumb").nth(2).click()
        assert "is-active" in view.locator(".strip-thumb").nth(2).get_attribute("class")
        assert "is-active" not in view.locator(".strip-thumb").first.get_attribute("class")

    def test_the_stage_says_when_it_is_showing_the_piece(self, page):
        """Third thumbnail is the piece's own; the first two are the colour's."""
        view, _ = page
        assert view.locator("#stage-note").is_hidden()

        view.locator(".strip-thumb").nth(2).click()
        assert view.locator("#stage-note").is_visible()
        assert "peça" in view.locator("#stage-note").inner_text()

        # On the photograph, not lost behind it: the note had no styles at all at
        # first and rendered as bare text at the top of the stage.
        note = view.locator("#stage-note").bounding_box()
        stage = view.locator("#gallery-stage").bounding_box()
        assert note["y"] > stage["y"] + stage["height"] / 2, "the note is not on the photo"
        assert view.locator("#stage-note").evaluate(
            "el => getComputedStyle(el).position"
        ) == "absolute"

        view.locator(".strip-thumb").first.click()
        assert view.locator("#stage-note").is_hidden()

    def test_choosing_the_marked_thumbnail_does_not_resize_its_neighbours(self, page):
        """The border is 2px in both states rather than growing when active."""
        view, _ = page
        before = view.locator(".strip-thumb").nth(1).bounding_box()
        view.locator(".strip-thumb").nth(1).click()
        after = view.locator(".strip-thumb").nth(1).bounding_box()

        assert (round(before["width"]), round(before["height"])) == (
            round(after["width"]), round(after["height"])
        )


class TestAColourWithNoPhotographsOfItsOwn:
    """Half the catalogue. The piece's own photographs are what there is, and the
    stage has to say so rather than passing one off as that colour."""

    def test_it_falls_back_to_the_piece_and_says_so(self, page):
        view, errors = page
        view.locator(".variant-option", has_text="Preto e Branco").click()
        view.wait_for_function(
            "() => document.querySelectorAll('#thumb-strip .strip-thumb').length === 1"
            " || document.getElementById('stage-note').hidden === false"
        )

        assert view.locator("#stage-note").is_visible()
        assert "peça" in view.locator("#stage-note").inner_text()
        assert errors == []

    def test_it_used_to_show_nothing_at_all(self, page):
        """The photograph is reachable, which is the point: with one image there is
        no strip to preview, but the stage is a real photograph rather than the
        placeholder tile."""
        view, _ = page
        view.locator(".variant-option", has_text="Preto e Branco").click()
        view.wait_for_timeout(300)

        assert view.locator("#stage-image").is_visible()
        assert view.locator("#gallery-stage .product-placeholder").count() == 0


class TestAPiecePhotographedOncePerColour:
    """Caixa Redonda Filigrana: four photographs, one on each of four colours.

    Each colour shows its own and nothing else, so there is nothing to preview and the
    strip stays away — the four are reached through the swatches, which is what the
    swatches are for.
    """

    @pytest.fixture()
    def spread(self, client, make_product, make_color, make_color_set):
        from tests.test_uploads import image_bytes

        product = make_product("Caixa Redonda Filigrana")
        white = make_color("Branco", hex="#FFFFFF")

        names = ["Branco e Dourado", "Preto e Branco", "Vermelho e Branco", "Azul e Branco"]
        for name in names:
            color_set = make_color_set(name, color_ids=[white["id"]])
            variant = client.post(
                f"/api/products/{product['id']}/variants",
                json={"color_set_id": color_set["id"]},
            ).get_json()
            response = client.post(
                f"/api/products/{product['id']}/images/upload",
                data={
                    "file": (io.BytesIO(image_bytes()), f"{name}.jpg"),
                    "variant_id": str(variant["id"]),
                },
                content_type="multipart/form-data",
            )
            assert response.status_code == 201, response.get_json()

        # A fifth colour nobody has photographed yet, and no photograph of the piece
        # either: the only case left where the stage has nothing real to show.
        unphotographed = make_color_set("Verde e Dourado", color_ids=[white["id"]])
        client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": unphotographed["id"]},
        )

        return product, names

    @pytest.fixture()
    def view(self, browser, live_server, spread):
        product, names = spread
        context = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(5000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{live_server}/products/{product['id']}")
        # Not the strip: a colour with one photograph has nothing to preview.
        page.wait_for_selector(".variant-option.is-active")
        yield page, names, errors
        context.close()

    def test_a_colour_nobody_has_photographed_shows_the_placeholder(self, view):
        """And not the photograph of the colour looked at before it: [hidden] is
        display: none, and an explicit display in a rule outranks it, so the previous
        colour's photograph stayed on the stage behind the placeholder."""
        page, _, _ = view
        page.locator(".variant-option", has_text="Verde e Dourado").click()
        page.wait_for_selector("#gallery-stage .product-placeholder")

        assert page.locator("#stage-image").is_hidden()
        assert page.locator("#stage-image").bounding_box() is None

    def test_only_the_chosen_colours_photograph_is_offered(self, view):
        """The gallery is about the colour chosen. It briefly offered every colour's
        photographs in an "Outras cores" group, which turned the page into a tour of
        the whole piece — another colour's photographs belong behind its swatch."""
        page, _, errors = view

        assert page.locator("#thumb-strip").is_hidden(), (
            "one photograph for this colour, so there is nothing to preview"
        )
        assert page.locator("#stage-counter").is_hidden()
        assert errors == []

    def test_the_arrows_stay_within_the_colour(self, view):
        page, _, _ = view
        assert page.locator("[data-prev]").is_disabled()
        assert page.locator("[data-next]").is_disabled()

    def test_another_colours_photograph_appears_by_choosing_that_colour(self, view):
        page, names, _ = view
        before = page.locator("#stage-image").get_attribute("src")

        page.locator(".variant-option", has_text=names[2]).click()
        page.wait_for_function(
            """(previous) => document.getElementById('stage-image').src !== previous""",
            arg=before,
        )

        assert page.locator("#stage-note").is_hidden(), (
            "it is this colour's own photograph, so nothing to disclaim"
        )


class TestTheTwoHalvesEndTogether:
    """The gallery takes its height from the panel beside it rather than setting it.

    A square stage made the left side taller than the right by however much the
    photograph exceeded the panel — 714px against 600 — leaving a column of dead space
    under the enquiry button.
    """

    def test_they_end_at_the_same_point(self, page):
        view, _ = page
        ends = view.evaluate(
            """() => {
                const columns = [...document.querySelectorAll('#product-detail > .column')];
                const lastVisible = (column) => [...column.children]
                    .filter((child) => child.getBoundingClientRect().height > 0)
                    .pop();
                return columns.map((column) =>
                    Math.round(lastVisible(column).getBoundingClientRect().bottom));
            }"""
        )
        assert abs(ends[0] - ends[1]) <= 2, f"the halves end {ends} apart"

    def test_the_photograph_is_not_what_decides_the_height(self, page):
        """An <img> at height: 100% falls back to its own aspect ratio while the height
        is being worked out, so in flow it went on setting the row's height."""
        view, _ = page
        assert view.locator("#stage-image").evaluate(
            "el => getComputedStyle(el).position"
        ) == "absolute"


class TestTheArrows:
    def test_they_are_icons_rather_than_punctuation(self, page):
        """They were ‹ and › characters, which needed 1.4rem to read as arrows."""
        view, _ = page

        for control in ("[data-prev]", "[data-next]"):
            button = view.locator(control)
            assert button.locator("i.fa-solid").count() == 1, control
            assert button.inner_text().strip() == "", f"{control} still has a glyph"

        assert view.locator("[data-prev] i").get_attribute("class") == "fa-solid fa-chevron-left"
        assert view.locator("[data-next] i").get_attribute("class") == "fa-solid fa-chevron-right"


class TestOnAPhone:
    @pytest.fixture()
    def phone(self, browser, live_server, piece):
        context = browser.new_context(viewport={"width": 390, "height": 780})
        view = context.new_page()
        view.set_default_timeout(5000)
        view.goto(f"{live_server}/products/{piece['id']}")
        view.wait_for_selector("#thumb-strip .strip-thumb")
        yield view
        context.close()

    def test_the_strip_is_a_row_the_page_does_not_scroll_sideways_for(self, phone):
        """It is a row at every width now, which is why the media query that turned
        the vertical rail into one could go."""
        state = phone.evaluate(
            """() => {
                const strip = document.getElementById('thumb-strip');
                return {
                    direction: getComputedStyle(strip).flexDirection,
                    overflowX: getComputedStyle(strip).overflowX,
                    pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
                };
            }"""
        )
        assert state["direction"] == "row"
        assert state["overflowX"] == "auto"
        assert not state["pageScrolls"]

    def test_the_photograph_still_fits(self, phone):
        stage = phone.locator("#gallery-stage").bounding_box()
        assert stage["width"] <= 390
