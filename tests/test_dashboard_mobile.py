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
        """Bulma's .navbar is only a flex row from 1024px up; below that it is a block,
        so the brand and the menu stacked and the user's control was drawn under the
        52px bar rather than in it."""
        page, errors = phone
        state = page.evaluate(
            """() => {
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const menu = document.querySelector('.dash-navbar-menu').getBoundingClientRect();
                const burger = document.getElementById('sidebarToggle').getBoundingClientRect();
                return {
                    barBottom: Math.round(bar.bottom),
                    menuBottom: Math.round(menu.bottom),
                    burgerBottom: Math.round(burger.bottom),
                    burgerRight: Math.round(burger.right),
                    viewport: window.innerWidth,
                };
            }"""
        )
        assert state["menuBottom"] <= state["barBottom"] + 1, "the menu hangs below the bar"
        assert state["burgerBottom"] <= state["barBottom"] + 1
        assert errors == []

    def test_the_burger_is_against_the_right_edge(self, phone):
        """It lives outside .navbar-brand for this: inside it, it could only ever be
        pushed to the brand's own right edge, which is the middle of the bar."""
        page, _ = phone
        state = page.evaluate(
            """() => ({
                burgerRight: Math.round(document.getElementById('sidebarToggle').getBoundingClientRect().right),
                viewport: window.innerWidth,
            })"""
        )
        assert state["viewport"] - state["burgerRight"] < 24, state

    def test_the_dropdown_opens_below_the_bar_and_on_top(self, phone):
        """A fixed navbar's menu has overflow: auto in Bulma so a stacked mobile menu
        can scroll, which clipped the dropdown out of existence — it had a box and was
        absent from elementsFromPoint."""
        page, _ = phone
        page.click("[data-dropdown-trigger]")

        state = page.evaluate(
            """() => {
                const menu = document.querySelector('.navbar-dropdown');
                const box = menu.getBoundingClientRect();
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const top = document.elementFromPoint(
                    box.x + box.width / 2, box.y + box.height / 2);
                return {
                    hasSize: box.height > 0,
                    startsAtTheBarsEdge: Math.abs(box.top - bar.bottom) <= 2,
                    withinViewport: box.right <= window.innerWidth && box.left >= 0,
                    isOnTop: menu.contains(top),
                };
            }"""
        )
        assert state["hasSize"], "the dropdown has no box"
        assert state["isOnTop"], "something is painted over the dropdown"
        assert state["startsAtTheBarsEdge"], state
        assert state["withinViewport"], state

    def test_the_burger_opens_the_sidebar(self, phone):
        page, _ = phone
        page.click("#sidebarToggle")
        # The class lands before the slide-in runs, so the box is still off-screen.
        page.wait_for_function(
            "() => document.getElementById('sidebar').getBoundingClientRect().x >= -1"
        )

        assert page.locator("#overlay.is-open").count() == 1


class TestTheModalScrollsItsOwnBody:
    def test_a_tall_panel_scrolls_inside_the_dialog(self, phone):
        """The max-height was on the <dialog>, which capped nothing inside it: the
        colours panel came out 1028px tall in a 732px dialog and the page scrolled
        behind instead of the dialog's content."""
        page, _ = phone
        page.evaluate("document.querySelector('#product-list tr[data-product-id]').click()")
        page.wait_for_selector("#editProductModal", state="visible")
        page.evaluate("document.querySelector('#edit-tabs li[data-tab]:last-child').click()")

        state = page.evaluate(
            """() => {
                const dialog = document.getElementById('editProductModal');
                const body = dialog.querySelector('.modal-card-body');
                return {
                    bodyWithinDialog:
                        body.getBoundingClientRect().height <= dialog.getBoundingClientRect().height,
                    bodyOverflow: getComputedStyle(body).overflowY,
                    pageLocked: getComputedStyle(document.documentElement).overflow,
                };
            }"""
        )
        assert state["bodyWithinDialog"], "the body is taller than the dialog holding it"
        assert state["bodyOverflow"] == "auto"
        assert state["pageLocked"] == "hidden", "the page behind can still scroll"

    def test_the_page_scrolls_again_once_it_closes(self, phone):
        page, _ = phone
        page.evaluate("document.querySelector('#product-list tr[data-product-id]').click()")
        page.wait_for_selector("#editProductModal", state="visible")
        page.keyboard.press("Escape")
        page.wait_for_selector("#editProductModal", state="hidden")

        assert page.evaluate(
            "() => getComputedStyle(document.documentElement).overflow"
        ) != "hidden"
