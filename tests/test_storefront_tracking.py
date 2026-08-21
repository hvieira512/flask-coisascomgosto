"""What the storefront records, in a real browser.

Every rule here is about *when* something counts, which is not a thing the
endpoint can decide: one view per piece per tab however often it is reloaded, an
enquiry carrying whatever was chosen at the moment of the click, a search recorded
with the number of pieces it found, and a filter only on the way on.

Recorded anonymously — the visitor has no session, and these tests never create
one.

`live_server` and `browser` come from conftest.py.
"""

import time
from urllib.parse import unquote

import pytest

pytest.importorskip("playwright.sync_api")


def events(kind=None, *, expected=1, timeout=5.0):
    """Wait for the event log to hold `expected` rows of `kind`, and return them.

    Its own connection each time, deliberately: the beacons are fire-and-forget,
    so there is nothing on the page to wait for, and the `cursor` fixture holds
    one transaction for the whole test — under MySQL's REPEATABLE READ it would
    keep answering with the snapshot it started with and never see them arrive.
    """
    from db import get_db_connection

    where = " WHERE kind = %s" if kind else ""
    params = (kind,) if kind else ()
    deadline = time.monotonic() + timeout
    rows = []

    while time.monotonic() < deadline:
        with get_db_connection() as (_, cursor):
            cursor.execute(
                f"SELECT * FROM storefront_events{where} ORDER BY id", params
            )
            rows = list(cursor.fetchall())
        if len(rows) >= expected:
            return rows
        time.sleep(0.05)

    raise AssertionError(
        f"waited {timeout}s for {expected} {kind or 'event'}(s), saw {len(rows)}"
    )


def no_more_than(kind, count):
    """Nothing else arrived. A short wait, since the point is a beacon that must
    not be sent — there is no signal to wait for, only its absence."""
    time.sleep(0.4)
    from db import get_db_connection

    from repositories.base import one_row

    with get_db_connection() as (_, cursor):
        cursor.execute(
            "SELECT COUNT(*) AS n FROM storefront_events WHERE kind = %s", (kind,)
        )
        assert one_row(cursor)["n"] == count


@pytest.fixture()
def catalogue(client, make_product, make_product_type, make_color, make_color_set):
    """Two pieces, one of them in two colours and one size."""
    box = make_product_type("Caixa")
    frame = make_product_type("Moldura")

    piece = make_product("Caixa Redonda", type_id=box["id"])
    make_product("Moldura Oval", type_id=frame["id"])

    variants = {}
    for name in ("Preto e Dourado", "Branco e Dourado"):
        color_set = make_color_set(name, [make_color(f"Cor {name}")["id"]])
        variants[name] = client.post(
            f"/api/products/{piece['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()

    sizes = client.get("/api/sizes/").get_json()["sizes"]
    client.put(
        f"/api/products/{piece['id']}/sizes", json={"size_ids": [sizes[0]["id"]]}
    )

    return {"piece": piece, "variants": variants, "size": sizes[0]}


@pytest.fixture()
def visitor(browser, live_server, catalogue):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page, errors, catalogue, live_server
    context.close()


class TestAView:
    def test_opening_a_piece_records_one(self, visitor):
        page, errors, catalogue, server = visitor

        page.goto(f"{server}/products/{catalogue['piece']['id']}")

        (row,) = events("view")
        assert row["product_id"] == catalogue["piece"]["id"]
        assert errors == []

    def test_reloading_does_not_record_another(self, visitor):
        """A reload is the same visit looking at the same thing. Without this the
        most-viewed list would rank whoever refreshed hardest."""
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        events("view")

        page.reload()
        page.reload()

        no_more_than("view", 1)

    def test_a_second_piece_records_its_own(self, visitor):
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        events("view")

        page.goto(f"{server}/products/{catalogue['piece']['id'] + 1}")

        assert len(events("view", expected=2)) == 2

    def test_a_new_tab_counts_again(self, visitor, browser, live_server):
        """The flag is per tab, which is the closest thing to "a visit" that can
        be had without identifying anybody."""
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        events("view")

        other = browser.new_context(viewport={"width": 1280, "height": 900})
        try:
            other.new_page().goto(f"{server}/products/{catalogue['piece']['id']}")
            assert len(events("view", expected=2)) == 2
        finally:
            other.close()

    def test_a_piece_that_does_not_exist_records_nothing(self, visitor):
        """The page shows its error notice; there is no view to count."""
        page, _, _, server = visitor

        page.goto(f"{server}/products/9999")
        page.wait_for_selector("#detail-error", state="visible")

        no_more_than("view", 0)


class TestAnEnquiry:
    def _ask(self, page):
        """Click through to WhatsApp without leaving the page."""
        link = page.locator("#enquiry-link")
        link.evaluate("el => el.removeAttribute('target')")
        link.evaluate("el => el.setAttribute('href', 'javascript:void 0')")
        link.click()

    def test_it_carries_the_colour_on_screen(self, visitor):
        """The colour is the whole value of this: it says which colourway to make
        next, not merely that somebody asked."""
        page, errors, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        page.wait_for_selector(".variant-option")

        page.locator(".variant-option", has_text="Branco e Dourado").click()
        self._ask(page)

        (row,) = events("enquiry")
        assert row["variant_id"] == catalogue["variants"]["Branco e Dourado"]["id"]
        assert errors == []

    def test_it_carries_the_size_too(self, visitor):
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        page.wait_for_selector("#size-options button")

        page.locator("#size-options button").first.click()
        self._ask(page)

        (row,) = events("enquiry")
        assert row["size_id"] == catalogue["size"]["id"]

    def test_asking_twice_counts_twice(self, visitor):
        """Unlike a view: asking again is asking again."""
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        page.wait_for_selector("#enquiry-link")

        self._ask(page)
        self._ask(page)

        assert len(events("enquiry", expected=2)) == 2

    def test_the_whatsapp_message_still_carries_the_choice(self, visitor):
        """The tracking rides along with the enquiry; it must not have replaced
        what the button was for."""
        page, _, catalogue, server = visitor
        page.goto(f"{server}/products/{catalogue['piece']['id']}")
        page.wait_for_selector(".variant-option")

        page.locator(".variant-option", has_text="Branco e Dourado").click()
        page.locator("#size-options button").first.click()

        message = unquote(page.locator("#enquiry-link").get_attribute("href"))

        assert "Branco e Dourado" in message
        assert catalogue["size"]["name"] in message


class TestASearch:
    def test_it_is_recorded_with_what_it_found(self, visitor):
        page, errors, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector("#product-grid .product-card")

        page.fill("#filter-search", "Caixa")

        (row,) = events("search")
        assert row["term"] == "caixa"
        assert row["results"] == 1, "one piece is called Caixa Redonda"
        assert errors == []

    def test_finding_nothing_is_the_interesting_case(self, visitor):
        """A list of things people want and the catalogue does not offer."""
        page, _, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector("#product-grid .product-card")

        page.fill("#filter-search", "tabuleiro de queijos")

        (row,) = events("search")
        assert row["term"] == "tabuleiro de queijos"
        assert row["results"] == 0

    def test_two_letters_are_somebody_still_typing(self, visitor):
        page, _, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector("#product-grid .product-card")

        page.fill("#filter-search", "ca")

        no_more_than("search", 0)

    def test_narrowing_it_further_does_not_record_it_again(self, visitor):
        """The grid refetches whenever anything changes, and the term rides along
        with every one of those requests. Only the term itself is a search."""
        page, _, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector("#product-grid .product-card")
        page.fill("#filter-search", "Caixa")
        events("search")

        # A filter on top of the same term: a second fetch, the same search.
        page.locator(".filter-entry", has_text="Caixa").first.click()
        events("filter")

        no_more_than("search", 1)


class TestAFilter:
    def test_ticking_one_records_the_group_and_the_label(self, visitor):
        page, errors, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector(".filter-entry")

        page.locator(".filter-entry", has_text="Caixa").first.click()

        (row,) = events("filter")
        assert row["facet"] == "Tipo", "the owners' word, not the API's type_id"
        assert row["facet_label"] == "Caixa"
        assert errors == []

    def test_unticking_it_records_nothing(self, visitor):
        """Turning a filter off is not a preference for anything, and counting it
        would double every visitor who changes their mind."""
        page, _, _, server = visitor
        page.goto(f"{server}/products")
        page.wait_for_selector(".filter-entry")
        entry = page.locator(".filter-entry", has_text="Caixa").first

        entry.click()
        events("filter")
        entry.click()

        no_more_than("filter", 1)

    def test_choosing_a_collection_from_the_rail_counts_too(
        self, visitor, client, make_collection
    ):
        """The rail is the only way to filter by collection, so it is the most used
        filter on the page."""
        page, _, catalogue, server = visitor
        collection = make_collection("Filigrana")
        client.put(
            f"/api/products/{catalogue['piece']['id']}",
            json={
                "name": catalogue["piece"]["name"],
                "description": "",
                "type_id": catalogue["piece"]["type"]["id"],
                "collection_id": collection["id"],
            },
        )

        page.goto(f"{server}/products")
        page.wait_for_selector(".collection-card")
        page.locator(".collection-card", has_text="Filigrana").first.click()

        (row,) = events("filter")
        assert (row["facet"], row["facet_label"]) == ("Colecção", "Filigrana")
