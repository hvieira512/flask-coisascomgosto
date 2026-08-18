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

    yield page, errors, {"filigrana": filigrana, "bordados": bordados}
    context.close()


def card(page, name):
    return page.locator(".collection-card", has_text=name).first


def shown(page):
    """How many pieces the grid is showing."""
    return page.locator("#product-grid > *").count()


class TestTheRail:
    def test_it_offers_every_collection_that_has_pieces(self, catalogue):
        page, errors, _ = catalogue
        names = page.locator(".collection-card-name").all_text_contents()

        assert names[0] == "Ver tudo", "getting back to everything comes first"
        assert "Filigrana" in names and "Bordados" in names
        assert "Vazia" not in names, "a collection with nothing behind it is a dead end"
        assert errors == []

    def test_the_grid_is_already_full_before_anything_is_chosen(self, catalogue):
        """The whole point of a rail rather than a gate."""
        page, _, _ = catalogue

        assert card(page, "Ver tudo").get_attribute("aria-pressed") == "true"
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
        assert card(page, "Ver tudo").get_attribute("aria-pressed") == "false"

    def test_it_drives_the_same_filter_as_the_sidebar(self, catalogue):
        """One piece of state, not a mode of its own: the badge, the sidebar entry
        and the URL all follow from the same selection, so Limpar tudo clears the
        rail too."""
        page, _, ids = catalogue
        card(page, "Filigrana").click()
        page.wait_for_function("() => location.search.includes('collection_id')")

        assert f"collection_id={ids['filigrana']['id']}" in page.url
        assert "Filigrana" in page.locator("#active-filters").inner_text()

        sidebar_entry = page.locator(
            '[data-facet="collections"] .filter-entry[aria-pressed="true"]'
        )
        assert "Filigrana" in sidebar_entry.inner_text()

        page.locator("#clear-filters").click()
        # The grid, not the URL: the URL is rewritten before the products are
        # fetched, so waiting on it races the reload.
        page.wait_for_function(
            "() => document.querySelectorAll('#product-grid > *').length === 4"
        )
        assert card(page, "Ver tudo").get_attribute("aria-pressed") == "true"

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
        assert card(page, "Ver tudo").get_attribute("aria-pressed") == "true"

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


class TestWhenThereIsNothingToChoose:
    def test_one_collection_is_not_a_choice(
        self, browser, live_server, client, make_collection, make_product
    ):
        """A rail with a single cover next to "Ver tudo" is furniture, not a
        decision, so it stays out of the way."""
        only = make_collection("Filigrana")
        make_product("Caixa", collection_id=only["id"])

        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{live_server}/products")
        page.wait_for_selector("#product-grid > *")

        assert not page.locator("#collection-rail").is_visible()
        context.close()
