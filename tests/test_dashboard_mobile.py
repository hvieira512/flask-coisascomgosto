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
def phone(browser, live_server, client, make_user, make_product,
          make_color, make_color_set):
    make_user("phone", password="Passw0rd!")
    product = make_product("Caixa Redonda")

    # Three colours with real names, because that is what a card has to fit: on
    # one line the chips truncated to "Branco …", which names no colour.
    for name in ("Branco e Dourado", "Preto e Dourado", "Vermelho e Branco"):
        color_set = make_color_set(name, [make_color(f"Cor {name}")["id"]])
        client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        )

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

    def test_the_bar_says_who_is_signed_in(self, phone):
        """It used to hide the username below 992px, on the stated grounds that the
        name was "inside the menu" — the menu held only Sair, so on a phone the
        dashboard never said whose it was. There is no shortage of room: the bar had
        208 free pixels beside the brand."""
        page, _ = phone
        state = page.evaluate(
            """() => {
                const name = document.querySelector('.dash-user-name');
                return {
                    text: name.textContent.trim(),
                    width: Math.round(name.getBoundingClientRect().width),
                    display: getComputedStyle(name).display,
                };
            }"""
        )
        assert state["text"] == "phone"
        assert state["width"] > 0, state
        assert state["display"] != "none"

    def test_the_menu_carries_the_name_in_full(self, phone):
        """The bar truncates a long one, so the dropdown is where it is readable."""
        page, _ = phone
        page.click("[data-dropdown-trigger]")
        page.wait_for_selector(".dropdown-menu.show")

        header = page.locator(".dropdown-menu.show .dropdown-header")
        assert header.inner_text().strip() == "phone"

    def test_a_long_name_gives_way_instead_of_breaking_the_bar(self, phone):
        """A .navbar wraps by default and this one has a fixed height, so anything
        that does not fit dropped onto a second line the bar then clipped: at 320px
        the burger ended up at x=183 of 320, under the brand."""
        page, _ = phone
        page.evaluate(
            "() => { document.querySelector('.dash-user-name').textContent ="
            " 'mariajoaodecarvalhoesilva'; }"
        )
        state = page.evaluate(
            """() => {
                const name = document.querySelector('.dash-user-name');
                const burger = document.getElementById('sidebarToggle').getBoundingClientRect();
                const brand = document.querySelector('.navbar-brand').getBoundingClientRect();
                return {
                    truncated: name.scrollWidth > name.clientWidth + 1,
                    burgerRight: Math.round(burger.right),
                    onTheBrandsLine: brand.right <= name.getBoundingClientRect().left,
                    viewport: window.innerWidth,
                };
            }"""
        )
        assert state["truncated"], "the name should ellipsize, not push"
        assert state["viewport"] - state["burgerRight"] < 24, state
        assert state["onTheBrandsLine"], "the bar wrapped onto a second line"

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


class TestARecordIsACard:
    """It was a 56rem table inside a wrapper that scrolled sideways, with nothing
    to say it scrolled, and the actions column started off-screen: the only way to
    reach Apagar on a 390px phone was to drag the table and hope.

    The markup is still a table — it is one on a real screen — so this is CSS, and
    all five dashboard listings become cards from the same rules.
    """

    def test_the_column_header_is_gone(self, phone):
        """A card carries its own labels; a header row above one column of cards
        labels nothing. It also used to be sticky here, which pinned it on top of
        the first piece."""
        page, _ = phone

        assert page.evaluate(
            "() => getComputedStyle(document.querySelector('.dash-table thead'))"
            ".display"
        ) == "none"

    def test_the_page_does_not_scroll_sideways(self, phone):
        """The honest test is trying to move it: documentElement.scrollWidth is
        inflated by any descendant scrollport and reported 524px on a page that
        cannot move at all."""
        page, _ = phone

        page.evaluate("() => window.scrollTo(300, 0)")

        assert page.evaluate("() => window.scrollX") == 0

    def test_the_records_wrapper_has_nothing_left_to_scroll(self, phone):
        page, _ = phone

        overflow = page.evaluate(
            """() => {
                const wrap = document.querySelector('.dash-table-wrap');
                return wrap.scrollWidth - wrap.clientWidth;
            }"""
        )

        assert overflow <= 1, "the table is still wider than its card"

    def test_every_action_is_on_screen(self, phone):
        """Editar and Apagar were the far right of a 56rem table."""
        page, _ = phone

        offscreen = page.evaluate(
            """(width) => [...document.querySelectorAll(
                    '#product-list tr [data-product-action]')]
                .filter(button => {
                    const box = button.getBoundingClientRect();
                    return box.right > width + 1 || box.left < 0 || box.width === 0;
                }).length""",
            PHONE["width"],
        )

        assert offscreen == 0

    def test_the_actions_are_visible_without_a_hover(self, phone):
        """They are revealed on hover on a real screen. A phone cannot hover, and
        `@media (hover: none)` describes the device rather than the width — a
        narrow window on a laptop still reports a mouse, and left an empty box
        where the only route to Editar should be."""
        page, _ = phone

        opacity = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'#product-list tr .dash-row-actions')).opacity"
        )

        assert opacity == "1"

    def test_a_card_is_a_card_and_not_a_row(self, phone):
        page, _ = phone
        shape = page.evaluate(
            """() => {
                const row = document.querySelector('#product-list tr');
                const style = getComputedStyle(row);
                const box = row.getBoundingClientRect();
                return {
                    display: style.display,
                    borderWidth: parseFloat(style.borderTopWidth),
                    radius: parseFloat(style.borderTopLeftRadius),
                    width: Math.round(box.width),
                };
            }"""
        )

        assert shape["display"] == "flex"
        assert shape["borderWidth"] >= 1
        assert shape["radius"] > 0
        assert shape["width"] <= PHONE["width"]

    def test_the_colour_names_are_not_truncated_to_nothing(self, phone):
        """On one line three chips came out "Branco …", "Preto …", "Preto …" — the
        colour is the whole point of the chip."""
        page, _ = phone
        page.wait_for_selector("#product-list .color-set-name")

        clipped = page.evaluate(
            """() => [...document.querySelectorAll('#product-list .color-set-name')]
                .filter(el => el.scrollWidth > el.clientWidth + 1).length"""
        )

        assert clipped == 0

    def test_tapping_a_card_still_opens_the_editor(self, phone):
        """The row click is how a record is opened, and it has to survive the row
        becoming a card."""
        page, _ = phone

        page.locator("#product-list tr[data-product-id]").first.click()

        page.wait_for_selector("#editProductModal.show", timeout=5000)
        assert page.locator("#editProductModal").is_visible()


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
