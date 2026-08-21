"""The collection rail on the catalogue, in a real browser.

The owners say people ask for their work by collection rather than by the kind of
object, so the collections are offered first, as photographs. It is a rail and not
a gate: the grid underneath is already full, which is the one thing these tests
have to keep true — a catalogue that shows nothing until something is clicked is a
different product.

`live_server` and `browser` come from conftest.py.
"""

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def catalogue(browser, live_server, client, make_collection, make_product):
    """Three collections with pieces behind them, and one piece belonging to none.

    The orphan matters: it is the case a hard gate would have hidden for good.
    """
    filigrana = make_collection("Filigrana")
    bordados = make_collection("Bordados")
    make_collection("Vazia")  # no pieces, so the rail must not offer it

    make_product("Caixa Redonda", collection_id=filigrana["id"])
    make_product("Caixa Quadrada", collection_id=filigrana["id"])
    make_product("Bastidor", collection_id=bordados["id"])
    make_product("Peça sem colecção")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.goto(f"{live_server}/products")
    page.wait_for_selector("#collection-strip .collection-card")
    # And the pieces. The rail and the grid are two fetches, and waiting only on
    # the rail counted the grid before it had arrived — which passed alone and
    # failed under the load of the whole suite.
    page.wait_for_function(
        "() => document.querySelectorAll('#product-grid > *').length === 4"
    )

    yield page, errors, {"filigrana": filigrana, "bordados": bordados}
    context.close()


def card(page, name):
    return page.locator(".collection-card", has_text=name).first


def shown(page):
    """How many pieces the grid is showing."""
    return page.locator("#product-grid > *").count()


def nothing_chosen(page):
    """No collection chosen, which is what the grid showing everything looks
    like. There is no "Ver tudo" tile to carry the state any more."""
    return page.locator('.collection-card[aria-pressed="true"]').count() == 0


class TestTheRail:
    def test_it_offers_every_collection_that_has_pieces(self, catalogue):
        page, errors, _ = catalogue
        names = page.locator(".collection-card-name").all_text_contents()

        # No "Ver tudo" tile: the grid below is already everything, and choosing
        # the chosen one again is how you get back to it.
        assert "Ver tudo" not in names
        assert "Filigrana" in names and "Bordados" in names
        assert "Vazia" not in names, "a collection with nothing behind it is a dead end"
        assert errors == []

    def test_the_grid_is_already_full_before_anything_is_chosen(self, catalogue):
        """The whole point of a rail rather than a gate."""
        page, _, _ = catalogue

        assert nothing_chosen(page)
        assert shown(page) == 4
        assert page.locator("#product-grid").is_visible()

    def test_the_piece_belonging_to_no_collection_is_reachable(self, catalogue):
        page, _, _ = catalogue
        assert page.locator("#product-grid", has_text="Peça sem colecção").count() == 1

    def test_choosing_one_filters_the_grid(self, catalogue):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        # The grid, not the URL. The URL is rewritten the moment the selection
        # changes, while the products arrive a fetch later — waiting on it passed
        # alone and failed under the load of the whole suite.
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 2"
        )

        assert shown(page) == 2
        assert card(page, "Filigrana").get_attribute("aria-pressed") == "true"
        assert not nothing_chosen(page)

    def test_the_sidebar_does_not_ask_the_same_question(self, catalogue):
        """The cards are the only way to choose a collection. A checkbox list beside
        them was the same question asked twice — and it carried the count and the
        selected tick that the card already carries."""
        page, _, _ = catalogue

        assert page.locator('[data-facet="collections"]').count() == 0
        labels = page.locator("#filter-groups .filter-group-label").all_text_contents()
        assert [label.strip() for label in labels] == ["Tipo", "Material"]

    def test_it_still_drives_the_ordinary_filter_state(self, catalogue):
        """One piece of state, not a mode of its own: the URL, the badge and Limpar
        tudo all follow from the same selection the sidebar's own groups use."""
        page, _, ids = catalogue
        card(page, "Filigrana").click()
        page.wait_for_function("() => location.search.includes('collection_id')")

        assert f"collection_id={ids['filigrana']['id']}" in page.url
        assert "Filigrana" in page.locator("#active-filters").inner_text()

        page.locator("#clear-filters").click()
        # The grid, not the URL: the URL is rewritten before the products are
        # fetched, so waiting on it races the reload.
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 4"
        )
        assert nothing_chosen(page)

    def test_choosing_another_replaces_rather_than_accumulates(self, catalogue):
        """The sidebar's checkboxes add up. A wall of covers reads as "pick one",
        so the rail behaves the way it looks."""
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_function("() => location.search.includes('collection_id')")
        card(page, "Bordados").click()
        page.wait_for_function("() => document.querySelectorAll('#product-grid > *').length === 1")

        assert page.url.count("collection_id") == 1
        assert card(page, "Filigrana").get_attribute("aria-pressed") == "false"

    def test_choosing_the_chosen_one_again_goes_back_to_everything(self, catalogue):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 2"
        )
        card(page, "Filigrana").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 4"
        )

        assert not page.url.endswith("collection_id=1")
        assert nothing_chosen(page)

    def test_every_card_is_the_same_shape(self, catalogue):
        """A cover is either a photograph or the no-photograph tile, and that tile
        carries its own square aspect-ratio — so the frame has to decide the shape
        or the photographed collections come out taller and every name sits at a
        different height."""
        page, _, _ = catalogue
        heights = page.eval_on_selector_all(
            ".collection-cover",
            "els => els.map(el => Math.round(el.getBoundingClientRect().height))",
        )
        assert len(set(heights)) == 1, heights

        tops = page.eval_on_selector_all(
            ".collection-card-name",
            "els => els.map(el => Math.round(el.getBoundingClientRect().top))",
        )
        assert len(set(tops)) == 1, tops


class TestTheChosenTile:
    """The chosen collection is marked on the tile, and marking it must not move
    anything: the ring is an outline rather than a border, so it is painted over
    the tile instead of adding to its box.

    It used to be a 2px navy border, drawn beneath the cover — which came out 1px
    over the photograph and 3px over the name, with a step where they met."""

    def test_the_chosen_tile_is_outlined(self, catalogue):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 2"
        )

        outline = page.locator('.collection-card[aria-pressed="true"]').evaluate(
            """el => {
                const s = getComputedStyle(el);
                return {width: s.outlineWidth, style: s.outlineStyle};
            }"""
        )
        assert outline["style"] == "solid"
        assert outline["width"] == "2px"

    def test_choosing_a_collection_does_not_move_anything(self, catalogue):
        page, _, _ = catalogue
        before = page.locator("#collection-strip").bounding_box()

        card(page, "Filigrana").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 2"
        )
        after = page.locator("#collection-strip").bounding_box()

        assert abs(before["height"] - after["height"]) < 1
        assert abs(before["y"] - after["y"]) < 1


class TestWhereTheAppliedFiltersLive:
    """On the heading line, beside the count they explain.

    They had a row of their own between the collections and the grid, so choosing
    anything pushed the pieces 48px down the page — on a heading line that was
    otherwise 1224px of empty space.
    """

    def test_they_sit_above_the_collections_not_between_them_and_the_grid(
        self, catalogue
    ):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_selector("#active-filters .filter-badge")

        badges = page.locator("#active-filters").bounding_box()
        rail = page.locator("#collection-rail").bounding_box()
        assert badges["y"] < rail["y"]

    def test_they_sit_next_to_the_count(self, catalogue):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_selector("#active-filters .filter-badge")

        badge = page.locator(".filter-badge").bounding_box()
        count = page.locator("#result-count").bounding_box()
        assert 0 <= count["x"] - (badge["x"] + badge["width"]) < 24, (
            "the badge drifted away from the number it explains"
        )

    def test_choosing_a_filter_does_not_push_the_grid_down(self, catalogue):
        """The whole point of the move. A badge taller than the heading's line box
        grew the row instead, which cost 5px of the same fault."""
        page, _, _ = catalogue
        before = page.locator("#product-grid").bounding_box()["y"]

        card(page, "Filigrana").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 2"
        )
        after = page.locator("#product-grid").bounding_box()["y"]

        assert round(before) == round(after)

    def test_a_badge_is_still_big_enough_to_hit(self, catalogue):
        """Shrinking it to fit the line must not shrink it below a target anyone
        can tap. The whole badge removes the filter, not just the ×."""
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_selector("#active-filters .filter-badge")

        badge = page.locator(".filter-badge").bounding_box()
        assert badge["height"] >= 24
        assert badge["width"] >= 24

    def test_clicking_the_badge_removes_the_filter(self, catalogue):
        page, _, _ = catalogue
        card(page, "Filigrana").click()
        page.wait_for_selector("#active-filters .filter-badge")

        page.locator(".filter-badge").click()
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 4"
        )
        assert page.locator("#active-filters").is_hidden()


class TestOnAPhone:
    @pytest.fixture()
    def phone(self, browser, live_server, client, make_collection, make_product):
        for name in ("Filigrana", "Bordados", "Lenços"):
            collection = make_collection(name)
            make_product(f"Peça {name}", collection_id=collection["id"])

        context = browser.new_context(viewport={"width": 390, "height": 780})
        page = context.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{live_server}/products")
        page.wait_for_selector("#collection-strip .collection-card")
        # And the pieces: the rail and the grid are two fetches, and waiting only
        # on the rail counted the grid before it had arrived.
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 3"
        )
        yield page
        context.close()

    def test_the_rail_scrolls_sideways_and_the_page_does_not(self, phone):
        """Four covers cannot fit across 390px, so the rail becomes a scrolling
        row — and it has to be the rail that scrolls, not the document."""
        state = phone.evaluate(
            """() => {
                const strip = document.getElementById('collection-strip');
                const style = getComputedStyle(strip);
                return {
                    display: style.display,
                    overflowX: style.overflowX,
                    snap: style.scrollSnapType,
                    railScrolls: strip.scrollWidth > strip.clientWidth,
                    pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
                };
            }"""
        )
        assert state["display"] == "flex"
        assert state["overflowX"] == "auto"
        assert "x" in state["snap"]
        assert state["railScrolls"]
        assert not state["pageScrolls"], "the catalogue must not scroll sideways"

    def test_the_grid_is_still_there_underneath(self, phone):
        assert phone.locator("#product-grid > *").count() == 3

    def test_several_filters_wrap_instead_of_squeezing_the_heading(self, phone):
        """The heading row is a wrapping flex container on purpose: a row that never
        wraps crushes the title instead. One short badge fits beside it at 390px; two
        do not,
        and they have to drop onto a line of their own rather than crush the title
        and the count or push the page sideways."""
        phone.locator(".collection-card", has_text="Filigrana").first.click()
        phone.wait_for_selector("#active-filters .filter-badge")
        phone.locator('[data-facet="types"] .filter-entry').first.click()
        phone.wait_for_function(
            "() => document.querySelectorAll('.filter-badge').length === 2"
        )

        title = phone.locator("h1").bounding_box()
        badges = phone.locator("#active-filters").bounding_box()

        assert badges["y"] >= title["y"] + title["height"] - 4, (
            "two badges stayed on the title's line and squeezed it"
        )
        assert not phone.evaluate(
            "() => document.documentElement.scrollWidth > window.innerWidth"
        ), "the catalogue must not scroll sideways"


class TestACrowdedRail:
    """Eight collections rather than the three the workshop has today.

    The rail began as a wrapping grid, which was tidy at three and fell apart at
    eight: a second, ragged row of three cards, 341px of rail, and the pieces pushed
    off the fold — which is the one thing a rail is supposed to protect. Worse, once
    it became a scrolling row it grew its own column instead of scrolling, because a
    grid column is a flex item and a flex item will not go narrower than its content,
    so the whole catalogue scrolled sideways.
    """

    NAMES = ["Filigrana", "Bordados", "Lenços", "Barra da Saia",
             "Coração de Viana", "Presépios", "Natal", "Casamento"]

    @pytest.fixture()
    def crowded(self, browser, live_server, client, make_collection, make_product):
        for name in self.NAMES:
            collection = make_collection(name)
            make_product(f"Peça de {name}", collection_id=collection["id"])

        context = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{live_server}/products")
        page.wait_for_selector("#collection-strip .collection-card")
        yield page
        context.close()

    def test_it_stays_one_row(self, crowded):
        tops = crowded.eval_on_selector_all(
            ".collection-card",
            "els => els.map(el => Math.round(el.getBoundingClientRect().top))",
        )
        assert len(set(tops)) == 1, f"the rail wrapped onto {len(set(tops))} rows"

    def test_the_rail_scrolls_and_the_catalogue_does_not(self, crowded):
        state = crowded.evaluate(
            """() => {
                const strip = document.getElementById('collection-strip');
                return {
                    railScrolls: strip.scrollWidth > strip.clientWidth,
                    stripFitsItsColumn:
                        strip.clientWidth <= strip.closest('.container').clientWidth,
                    pageScrolls:
                        document.documentElement.scrollWidth > window.innerWidth,
                };
            }"""
        )
        assert state["railScrolls"], "nine cards must scroll, not squeeze"
        assert state["stripFitsItsColumn"], "the rail grew past its container"
        assert not state["pageScrolls"], "the catalogue must not scroll sideways"

    def test_the_pieces_are_still_on_the_fold(self, crowded):
        grid = crowded.locator("#product-grid").bounding_box()
        assert grid["y"] < 500, f"the grid starts at {grid['y']}px"

    def test_the_counts_line_up_even_when_a_name_wraps(self, crowded):
        """"Coração de Viana" takes two lines in a crowded rail where "Natal" takes
        one, so the count is pinned to the bottom of the card rather than following
        the name."""
        bottoms = crowded.eval_on_selector_all(
            ".collection-card-detail",
            "els => els.map(el => Math.round(el.getBoundingClientRect().bottom))",
        )
        assert len(set(bottoms)) == 1, bottoms

    def test_a_few_collections_still_fill_the_width(self, catalogue):
        """The other end of the same rule: three collections must not become three
        narrow cards with a gap where the rest of the row would be."""
        page, _, _ = catalogue
        widths = page.eval_on_selector_all(
            ".collection-card",
            "els => els.map(el => Math.round(el.getBoundingClientRect().width))",
        )
        strip = page.locator("#collection-strip").bounding_box()

        assert len(set(widths)) == 1, widths
        assert sum(widths) > strip["width"] * 0.9, "the row left the column half empty"


class TestWhenThereIsNothingToChoose:
    def _catalogue(self, browser, live_server):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{live_server}/products")
        page.wait_for_selector("#product-grid > *")
        return context, page

    def test_a_single_collection_still_gets_a_rail(
        self, browser, live_server, client, make_collection, make_product
    ):
        """It used to hide below two collections, on the grounds that one cover
        beside "Ver tudo" is furniture rather than a decision. That reasoning died
        with the sidebar's Colecção group: the rail is now the only way to filter by
        collection, so hiding it removes the filter instead of tidying it away."""
        only = make_collection("Filigrana")
        make_product("Caixa", collection_id=only["id"])
        make_product("Peça sem colecção")

        context, page = self._catalogue(browser, live_server)
        try:
            page.wait_for_selector("#collection-strip .collection-card")
            names = page.locator(".collection-card-name").all_text_contents()
            assert names == ["Filigrana"]
        finally:
            context.close()

    def test_no_collections_at_all_hides_it(
        self, browser, live_server, client, make_product
    ):
        """Nothing to choose between, so the rail is not drawn — and the catalogue
        is still a catalogue."""
        make_product("Caixa")

        context, page = self._catalogue(browser, live_server)
        try:
            assert not page.locator("#collection-rail").is_visible()
            assert page.locator("#product-grid > *").count() == 1
        finally:
            context.close()
