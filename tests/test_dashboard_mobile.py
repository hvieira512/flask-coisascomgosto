"""The dashboard's chrome at phone width, in a real browser.

Everything here was reported by the owners on a phone and none of it was covered:
the user's dropdown drawn outside the bar, the burger stranded mid-bar, and a modal
whose body pushed past the dialog so the page scrolled behind it instead.

`live_server` and `browser` come from conftest.py.
"""

import json

import pytest

pytest.importorskip("playwright.sync_api")

PHONE = {"width": 390, "height": 780}


@pytest.fixture()
def phone(browser, live_server, client, make_user, make_product):
    make_user("phone", password="Passw0rd!")
    make_product("Caixa Redonda")

    context = browser.new_context(viewport=PHONE)
    context.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "phone", "password": "Passw0rd!"}),
        headers={"Content-Type": "application/json"},
    )
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{live_server}/dashboard/products")
    page.wait_for_selector("#product-list tr[data-product-id]")
    yield page, errors
    context.close()


class TestTheNavbar:
    def test_everything_stays_inside_the_bar(self, phone):
        """Under Bulma the bar was only a flex row from 1024px up; below that the
        brand and the menu stacked and the user's control was drawn under the 52px
        bar rather than in it. Bootstrap's navbar is a row at every width."""
        page, errors = phone
        state = page.evaluate(
            """() => {
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const user = document.querySelector('.dash-user-btn').getBoundingClientRect();
                const burger = document.getElementById('sidebarToggle').getBoundingClientRect();
                return {
                    barBottom: Math.round(bar.bottom),
                    userBottom: Math.round(user.bottom),
                    burgerBottom: Math.round(burger.bottom),
                };
            }"""
        )
        assert state["userBottom"] <= state["barBottom"] + 1, "the control hangs below"
        assert state["burgerBottom"] <= state["barBottom"] + 1
        assert errors == []

    def test_the_burger_is_against_the_right_edge(self, phone):
        """It is the last thing in the bar, which is where a thumb expects it."""
        page, _ = phone
        state = page.evaluate(
            """() => ({
                burgerRight: Math.round(document.getElementById('sidebarToggle').getBoundingClientRect().right),
                viewport: window.innerWidth,
            })"""
        )
        assert state["viewport"] - state["burgerRight"] < 24, state

    def test_the_dropdown_opens_below_the_bar_and_on_top(self, phone):
        """It used to be drawn and then clipped out of existence by the fixed bar's
        own overflow: a box, opacity 1, and absent from elementsFromPoint. Popper
        places it against the trigger instead."""
        page, _ = phone
        page.click("[data-dropdown-trigger]")
        page.wait_for_selector(".dropdown-menu.show")

        state = page.evaluate(
            """() => {
                const menu = document.querySelector('.dropdown-menu.show');
                const box = menu.getBoundingClientRect();
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const top = document.elementFromPoint(
                    box.x + box.width / 2, box.y + box.height / 2);
                return {
                    hasSize: box.height > 0,
                    belowTheBar: box.top >= bar.bottom - 2,
                    withinViewport: box.right <= window.innerWidth && box.left >= 0,
                    isOnTop: menu.contains(top),
                };
            }"""
        )
        assert state["hasSize"], "the dropdown has no box"
        assert state["isOnTop"], "something is painted over the dropdown"
        assert state["belowTheBar"], state
        assert state["withinViewport"], state

    def test_the_burger_opens_the_sidebar(self, phone):
        """The offcanvas brings its own backdrop, so there is no #overlay of ours."""
        page, _ = phone
        page.click("#sidebarToggle")
        page.wait_for_selector("#sidebar.show")
        # The class lands before the slide-in runs, so the box is still off-screen.
        page.wait_for_function(
            "() => document.getElementById('sidebar').getBoundingClientRect().x >= -1"
        )

        assert page.locator(".offcanvas-backdrop").count() == 1
        assert page.locator("#sidebar .nav-link.active").count() == 1


class TestTheTable:
    def test_the_first_row_is_not_behind_the_header(self, phone):
        """The header is sticky on a desktop, where the page is the scrollport. At
        this width the table's own wrapper is the scrollport, so sticky pinned the
        header 52px down inside it — on top of the first piece in the catalogue.
        The override lives after the rule it overrides: at equal specificity the
        later declaration wins, and it lost silently the other way round."""
        page, _ = phone
        state = page.evaluate(
            """() => {
                const th = document.querySelector('.dash-table thead th');
                const first = document.querySelector('#product-list tr');
                return {
                    position: getComputedStyle(th).position,
                    headBottom: Math.round(th.getBoundingClientRect().bottom),
                    firstTop: Math.round(first.getBoundingClientRect().top),
                };
            }"""
        )
        assert state["position"] == "static"
        assert state["firstTop"] >= state["headBottom"] - 1, state


class TestTheModalScrollsItsOwnBody:
    def test_a_tall_panel_scrolls_inside_the_dialog(self, phone):
        """The max-height was on the <dialog>, which capped nothing inside it: the
        colours panel came out 1028px tall in a 732px dialog and the page scrolled
        behind instead of the dialog's content."""
        page, _ = phone
        page.evaluate("document.querySelector('#product-list tr[data-product-id]').click()")
        page.wait_for_selector("#editProductModal", state="visible")
        page.click('#edit-tabs li[data-tab="variants"] .nav-link')

        state = page.evaluate(
            """() => {
                const dialog = document.getElementById('editProductModal');
                const body = dialog.querySelector('.modal-body');
                return {
                    bodyWithinDialog:
                        body.getBoundingClientRect().height <= dialog.getBoundingClientRect().height,
                    bodyOverflow: getComputedStyle(body).overflowY,
                    // Bootstrap locks the scroll on <body>, not on <html>.
                    pageLocked: getComputedStyle(document.body).overflow,
                    modalOpen: document.body.classList.contains('modal-open'),
                };
            }"""
        )
        assert state["bodyWithinDialog"], "the body is taller than the dialog holding it"
        assert state["bodyOverflow"] == "auto", (
            "modal-dialog-scrollable is what makes the body the scroller"
        )
        assert state["modalOpen"]
        assert state["pageLocked"] == "hidden", "the page behind can still scroll"

    def test_the_page_scrolls_again_once_it_closes(self, phone):
        page, _ = phone
        page.evaluate("document.querySelector('#product-list tr[data-product-id]').click()")
        page.wait_for_selector("#editProductModal", state="visible")
        # Escape is handled on the modal element, so it has to hold focus first.
        page.wait_for_function(
            "() => document.getElementById('editProductModal').contains(document.activeElement)"
        )
        page.keyboard.press("Escape")
        page.wait_for_selector("#editProductModal", state="hidden")
        # The lock lifts when the backdrop has finished fading, which is after the
        # modal itself is already display: none.
        page.wait_for_function(
            "() => !document.body.classList.contains('modal-open')"
        )

        assert page.evaluate(
            "() => getComputedStyle(document.body).overflow"
        ) != "hidden"
        assert page.locator(".modal-backdrop").count() == 0
