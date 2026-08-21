"""Filtering the catalogue without a mouse, in a real browser.

The sidebar entries are `<a>` elements with no href, so they were not focusable
and not announced: unreachable by keyboard, while the badges that *remove* the
same filters were `role="button" tabindex="0"`. A keyboard user could undo a
filter they had never been able to apply.

They are also cumulative — several colours at once — which is a checkbox and not
a toggle button, so they carry `role="checkbox"` and `aria-checked` rather than
`aria-pressed`.

`live_server` and `browser` come from conftest.py.
"""

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def catalogue(browser, live_server, client, make_product, make_product_type):
    """Two types with pieces, so there is more than one thing to tick."""
    box = make_product_type("Caixa")
    frame = make_product_type("Moldura")
    make_product("Caixa Redonda", type_id=box["id"])
    make_product("Caixa de Joias", type_id=box["id"])
    make_product("Moldura Oval", type_id=frame["id"])

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.goto(f"{live_server}/products")
    page.wait_for_selector(".filter-entry")
    yield page, errors
    context.close()


def entry(page, name):
    return page.locator(".filter-entry", has_text=name).first


def shown(page):
    return page.locator("#product-grid .product-card").count()


def wait_for_cards(page, expected):
    """The grid is refetched when a filter changes, so counting straight after a
    keypress counts the old grid."""
    page.wait_for_function(
        """(expected) =>
            document.querySelectorAll('#product-grid .product-card').length
                === expected""",
        arg=expected,
    )


def focus_by_tab(page, limit=40):
    """Tab from the search box until a filter entry has focus, and return it.

    Pressing Tab rather than calling .focus(): only real keyboard interaction
    makes :focus-visible match, which is what draws the ring.
    """
    page.locator("#filter-search").focus()

    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate(
            "() => document.activeElement?.classList.contains('filter-entry')"
        ):
            return
    raise AssertionError(f"{limit} tabs from the search box and no filter was reached")


class TestTheEntriesAreReachable:
    def test_every_entry_with_pieces_is_focusable(self, catalogue):
        page, _ = catalogue

        tabindexes = page.locator(".filter-entry:not(.is-empty)").evaluate_all(
            "els => els.map(el => el.getAttribute('tabindex'))"
        )

        assert tabindexes, "no filter entries rendered"
        assert set(tabindexes) == {"0"}

    def test_an_entry_with_nothing_behind_it_is_skipped(
        self, browser, live_server, client, make_product_type, make_product
    ):
        """It stays listed — it is part of the workshop's vocabulary — but ticking
        it could only empty the grid, so it is not a stop on the way."""
        make_product_type("Tipo vazio")
        make_product("Uma peça")

        page = browser.new_page()
        page.goto(f"{live_server}/products")
        page.wait_for_selector(".filter-entry")

        empty = page.locator(".filter-entry.is-empty").first
        assert empty.count() == 1 or empty.is_visible()
        assert empty.get_attribute("tabindex") == "-1"
        assert empty.get_attribute("aria-disabled") == "true"
        page.close()

    def test_tabbing_reaches_one(self, catalogue):
        """Not simply focusable in the DOM: actually arrived at by pressing Tab."""
        page, _ = catalogue

        focus_by_tab(page)

        assert page.evaluate(
            "() => document.activeElement.getAttribute('role')"
        ) == "checkbox"


class TestItAnnouncesItselfAsACheckbox:
    def test_the_role_and_state_are_on_the_entry(self, catalogue):
        page, _ = catalogue
        first = page.locator(".filter-entry").first

        assert first.get_attribute("role") == "checkbox"
        assert first.get_attribute("aria-checked") == "false"

    def test_ticking_it_updates_the_state(self, catalogue):
        page, _ = catalogue
        target = entry(page, "Caixa")

        target.click()
        page.wait_for_function(
            "() => document.querySelector('.filter-entry.is-active') !== null"
        )

        assert target.get_attribute("aria-checked") == "true"

    def test_it_is_not_a_toggle_button(self, catalogue):
        """aria-pressed would say "one of these, on or off"; these add up."""
        page, _ = catalogue

        assert page.locator(".filter-entry[aria-pressed]").count() == 0


class TestTheKeyboardDoesWhatTheMouseDoes:
    def test_space_ticks_the_focused_entry(self, catalogue):
        page, errors = catalogue
        before = shown(page)
        target = entry(page, "Caixa")

        target.focus()
        page.keyboard.press(" ")
        wait_for_cards(page, 2)   # the two Caixa pieces

        assert target.get_attribute("aria-checked") == "true"
        assert before == 3
        assert errors == []

    def test_space_again_unticks_it(self, catalogue):
        page, _ = catalogue
        target = entry(page, "Caixa")
        target.focus()
        page.keyboard.press(" ")
        page.wait_for_selector(".filter-entry.is-active")

        page.keyboard.press(" ")
        wait_for_cards(page, 3)

        assert target.get_attribute("aria-checked") == "false"

    def test_enter_works_too(self, catalogue):
        """Not required for a checkbox, but it is what a keyboard user tries on
        something that looks like a link."""
        page, _ = catalogue
        target = entry(page, "Moldura")

        target.focus()
        page.keyboard.press("Enter")
        wait_for_cards(page, 1)

        assert target.get_attribute("aria-checked") == "true"

    def test_space_does_not_scroll_the_page(self, catalogue):
        """The default action for Space is a page-down, which would take the
        sidebar out from under the person using it."""
        page, _ = catalogue
        entry(page, "Caixa").focus()

        page.keyboard.press(" ")
        page.wait_for_selector(".filter-entry.is-active")

        assert page.evaluate("() => window.scrollY") == 0

    def test_two_can_be_ticked_at_once(self, catalogue):
        """The reason these are checkboxes: ticking Moldura must not untick
        Caixa."""
        page, _ = catalogue

        entry(page, "Caixa").focus()
        page.keyboard.press(" ")
        page.wait_for_selector(".filter-entry.is-active")
        entry(page, "Moldura").focus()
        page.keyboard.press(" ")
        page.wait_for_function(
            "() => document.querySelectorAll('.filter-entry.is-active').length === 2"
        )
        wait_for_cards(page, 3)   # both families, which is everything here

        assert entry(page, "Caixa").get_attribute("aria-checked") == "true"
        assert entry(page, "Moldura").get_attribute("aria-checked") == "true"

    def test_a_focused_entry_is_visibly_focused(self, catalogue):
        """An <a> with no href gets no focus ring from the browser, so one had to
        be given: focus that cannot be seen is the same as no focus.

        Reached by Tab, because :focus-visible only matches keyboard focus — and
        read off the element itself, since getComputedStyle takes a pseudo-element
        and not a pseudo-class, so asking it for ':focus-visible' returns nothing
        whatever the rule says.
        """
        page, _ = catalogue

        focus_by_tab(page)

        shadow = page.evaluate(
            "() => getComputedStyle(document.activeElement).boxShadow"
        )
        assert shadow and shadow != "none", "no visible focus on the filter"
