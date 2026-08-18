"""Behavioural tests for core/steps.js and core/modal.js, in a real browser.

Every other frontend test in this suite reads the source and asserts on its text,
which catches a call that went missing but never a dialog that does not open. These
run the modules.

A real browser rather than a DOM library, for two reasons. jsdom does not implement
`HTMLDialogElement.showModal()`, which is the entire foundation of core/modal.js —
the focus trap, Escape, the backdrop and returning focus all come from it. And it
has no layout or cascade, so it cannot see the class of bug these dialogs actually
hit: `back.hidden = true` did nothing because Bulma's `.button` is
`display: inline-flex` and outranks the attribute. `is_visible()` below is computed
from real layout with the real stylesheets, so it fails on exactly that.

Requires `playwright install chromium`; the whole module skips without it.
"""

import json

import pytest

# `live_server` and `browser` are in conftest.py, shared with the storefront tests.
pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def signed_in(browser, live_server, make_user):
    """A page already through the login guard.

    The credential is this test's own throwaway user. Logging in through the
    context's request API rather than the form keeps the cookie jar shared with
    the page while skipping a screen these tests are not about.
    """
    make_user("browser", password="Passw0rd!")

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    response = context.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "browser", "password": "Passw0rd!"}),
        headers={"Content-Type": "application/json"},
    )
    assert response.ok, response.text()

    page = context.new_page()
    # Playwright waits 30s by default. Everything here is a local dialog opening,
    # so a wait that long only means a broken build takes half a minute per test
    # to say so.
    page.set_default_timeout(5000)

    # A failing module is otherwise a silent no-op: the button does nothing and
    # the test reports a missing element rather than the SyntaxError behind it.
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{live_server}/dashboard/home")

    yield page, errors
    context.close()


@pytest.fixture()
def products_page(signed_in, live_server, make_product_type):
    """The catalogue, with a type in the database so Tipo has something to pick."""
    make_product_type("Caixa")

    page, errors = signed_in
    page.goto(f"{live_server}/dashboard/products")
    page.wait_for_selector("#new-product")
    return page, errors


def _open_wizard(page):
    page.click("#new-product")
    dialog = page.locator("#newProductModal")
    dialog.wait_for(state="visible")
    return dialog


class TestStepDialog:
    """core/steps.js, driven the way an owner drives it."""

    def test_it_opens_on_the_first_step_with_no_way_back(self, products_page):
        page, errors = products_page
        dialog = _open_wizard(page)

        assert "Passo 1 de 2" in dialog.locator("[data-step-label]").text_content()
        assert dialog.locator("[data-step-progress]").get_attribute("value") == "1"

        # The one that regressed: Bulma's .button outranks [hidden], so this has
        # to be a real visibility check rather than an attribute read.
        assert not dialog.locator("[data-step-back]").is_visible()
        assert dialog.locator("[data-step-next]").inner_text().strip() == "Continuar"
        assert errors == []

    def test_the_first_step_keeps_its_required_fields(self, products_page):
        page, _ = products_page
        dialog = _open_wizard(page)

        # Nothing filled in at all.
        dialog.locator("[data-step-next]").click()
        page.wait_for_selector(".swal2-container")
        assert "nome é obrigatório" in page.locator(".swal2-container").inner_text()
        assert "Passo 1 de 2" in dialog.locator("[data-step-label]").text_content()

        # A name but no type still is not enough.
        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator("[data-step-next]").click()
        page.wait_for_timeout(300)
        assert "tipo é obrigatório" in page.locator(".swal2-container").inner_text()
        assert "Passo 1 de 2" in dialog.locator("[data-step-label]").text_content()

    def test_the_error_lands_in_front_of_the_dialog_not_behind_it(self, products_page):
        """A showModal() dialog is in the top layer, which paints above every
        z-index — so a toast appended to <body> came out behind its own backdrop.
        The owner picked a type, left the name empty, was refused, and could not
        see why.

        elementFromPoint is the only assertion that catches this: the toast is
        present, sized and styled either way. The question is what a person
        actually sees at those coordinates.
        """
        page, _ = products_page
        dialog = _open_wizard(page)

        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()
        page.wait_for_selector(".swal2-container")

        on_top = page.evaluate(
            """() => {
                // The popup, not the container: the container is a full-height
                // pointer-events:none frame, so its centre is empty air and would
                // report the dialog behind it either way.
                const toast = document.querySelector('.swal2-popup');
                const box = toast.getBoundingClientRect();
                const hit = document.elementFromPoint(
                    box.x + box.width / 2, box.y + box.height / 2);
                return { covered: !toast.contains(hit), inTopLayer: !!toast.closest('dialog') };
            }"""
        )
        assert not on_top["covered"], "the message is painting behind the dialog"
        assert on_top["inTopLayer"], "only the top layer can sit above a modal dialog"

    def test_advancing_swaps_which_group_is_on_screen(self, products_page):
        page, _ = products_page
        dialog = _open_wizard(page)

        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()

        assert "Passo 2 de 2" in dialog.locator("[data-step-label]").text_content()
        assert dialog.locator("[data-step-progress]").get_attribute("value") == "2"
        assert not dialog.locator('[name="name"]').is_visible()
        assert dialog.locator('[name="description"]').is_visible()
        assert dialog.locator("[data-step-back]").is_visible()
        assert dialog.locator("[data-step-next]").inner_text().strip() == "Criar produto"

    def test_going_back_keeps_every_answer(self, products_page):
        """The groups stay in the DOM precisely so this holds. Re-rendering the
        step would be simpler to write and would silently discard typing."""
        page, _ = products_page
        dialog = _open_wizard(page)

        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()

        dialog.locator('[name="description"]').fill("Com filigrana na tampa.")
        dialog.locator("[data-step-back]").click()

        assert dialog.locator('[name="name"]').input_value() == "Caixa Redonda"
        dialog.locator("[data-step-next]").click()
        assert (
            dialog.locator('[name="description"]').input_value()
            == "Com filigrana na tampa."
        )

    def test_nothing_is_written_until_the_last_step(self, products_page, live_server):
        """A piece is on the storefront the moment its row exists and there is no
        draft flag, so abandoning the wizard must leave nothing behind."""
        page, _ = products_page

        def product_count():
            body = page.request.get(f"{live_server}/api/products/").json()
            return body["pagination"]["total"]

        assert product_count() == 0

        dialog = _open_wizard(page)
        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()
        assert product_count() == 0, "reaching the last step must not create it"

        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        assert product_count() == 0, "abandoning the wizard must not create it"

    def test_the_last_step_writes_once_and_hands_over_to_the_colours(
        self, products_page, live_server
    ):
        page, errors = products_page
        dialog = _open_wizard(page)

        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")

        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["pagination"]["total"] == 1
        assert body["products"][0]["name"] == "Caixa Redonda"

        # Landing on Detalhes would show the owner the form they just filled.
        assert edit.locator("#edit-tabs li.is-active").inner_text().strip() == "Cores"
        assert edit.locator('[data-panel="variants"]').is_visible()
        assert not edit.locator('[data-panel="details"]').is_visible()
        assert errors == []

    def test_editing_shows_both_groups_at_once(self, products_page, live_server):
        """Editing is changing one thing, so it is not a sequence: both groups are
        on screen and there is no step chrome."""
        page, _ = products_page
        dialog = _open_wizard(page)

        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator('[name="type_id"]').select_option(label="Caixa")
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")
        edit.locator('#edit-tabs [data-tab="details"]').click()

        assert edit.locator('[name="name"]').is_visible()
        assert edit.locator('[name="description"]').is_visible()
        assert edit.locator("[data-step-label]").count() == 0


class TestConfirmRaisedFromInsideADialog:
    """Removing a colour asks "Remover esta cor?" while the edit dialog is open.

    The question is rendered inside that dialog so it is not painted behind the
    backdrop, which means two overlay systems are nested and both listen for
    Escape. Whatever happens, the caller must not be left awaiting a promise that
    never settles.
    """

    def _confirm_over_the_edit_dialog(self, page, live_server):
        page.goto(f"{live_server}/dashboard/products")
        page.wait_for_selector("#product-list tr[data-product-id]")
        page.locator("#product-list tr[data-product-id]").first.click()

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")
        page.evaluate(
            """async () => {
                const { Notify } = await import('/static/js/core/notify.js');
                window.__answer = 'pending';
                Notify.confirm('Remover esta cor?', { danger: true })
                    .then(value => { window.__answer = value; });
            }"""
        )
        page.wait_for_selector(".swal2-popup")
        return edit

    def test_it_paints_over_the_dialog_it_was_raised_from(
        self, signed_in, live_server, make_product
    ):
        make_product("Caixa Redonda")
        page, _ = signed_in
        self._confirm_over_the_edit_dialog(page, live_server)

        state = page.evaluate(
            """() => {
                const popup = document.querySelector('.swal2-popup');
                const box = popup.getBoundingClientRect();
                const hit = document.elementFromPoint(
                    box.x + box.width / 2, box.y + box.height / 2);
                const button = [...popup.querySelectorAll('button')]
                    .find(b => b.textContent.trim() === 'Confirmar' ||
                               b.textContent.trim() === 'Cancelar');
                const rect = button.getBoundingClientRect();
                const overButton = document.elementFromPoint(
                    rect.x + rect.width / 2, rect.y + rect.height / 2);
                return {
                    covered: !popup.contains(hit),
                    buttonReachable: button.contains(overButton) || button === overButton,
                };
            }"""
        )
        assert not state["covered"]
        assert state["buttonReachable"], "a question nobody can answer is worse than none"

    def test_escape_settles_the_promise_instead_of_stranding_it(
        self, signed_in, live_server, make_product
    ):
        """Both overlays listen for Escape. If the dialog wins and takes the
        question down with it, the await never returns and the caller is wedged
        forever with no way to retry."""
        make_product("Caixa Redonda")
        page, _ = signed_in
        self._confirm_over_the_edit_dialog(page, live_server)

        page.keyboard.press("Escape")
        page.wait_for_function("() => window.__answer !== 'pending'")

        assert page.evaluate("window.__answer") is False, "Escape means no"

    def test_cancel_settles_the_promise_and_leaves_the_dialog_open(
        self, signed_in, live_server, make_product
    ):
        make_product("Caixa Redonda")
        page, _ = signed_in
        edit = self._confirm_over_the_edit_dialog(page, live_server)

        page.locator(".swal2-cancel").click()
        page.wait_for_function("() => window.__answer !== 'pending'")

        assert page.evaluate("window.__answer") is False
        assert edit.is_visible(), "answering the question must not close the form"


@pytest.fixture()
def types_page(signed_in, live_server):
    page, errors = signed_in
    page.goto(f"{live_server}/dashboard/types")
    page.wait_for_selector("#new-type")
    return page, errors


class TestModalHelpers:
    """core/modal.js: what showModal() buys, and what formDialog wires."""

    def test_opening_starts_in_the_first_field_not_on_the_close_button(
        self, types_page
    ):
        """The browser focuses the first focusable element, which is the ×  —
        leaving Enter wired to "close the dialog I have just opened"."""
        page, _ = types_page
        page.click("#new-type")
        page.locator("#newTypeModal").wait_for(state="visible")

        assert page.evaluate("document.activeElement.id") == "tf-name"

    def test_escape_closes_it_and_the_markup_stays(self, types_page):
        """Escape is the native dialog's, not ours. The dialog staying in the DOM
        is why every form inside one has to be looked up through its own modal."""
        page, _ = types_page
        page.click("#new-type")
        dialog = page.locator("#newTypeModal")
        dialog.wait_for(state="visible")

        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        assert dialog.count() == 1
        assert page.evaluate("document.getElementById('newTypeModal').open") is False

    def test_a_click_on_the_backdrop_still_closes_it(self, types_page):
        """The other half of the rule that closing Cancelar broke: a click beside
        the card is a dismissal, and ::backdrop has no click of its own."""
        page, _ = types_page
        page.click("#new-type")
        dialog = page.locator("#newTypeModal")
        dialog.wait_for(state="visible")

        page.mouse.click(8, 8)
        dialog.wait_for(state="hidden")
        assert page.evaluate("document.getElementById('newTypeModal').open") is False

    def test_a_click_inside_the_card_does_not_close_it(self, types_page):
        page, _ = types_page
        page.click("#new-type")
        dialog = page.locator("#newTypeModal")
        dialog.wait_for(state="visible")

        dialog.locator(".modal-card-body").click(position={"x": 4, "y": 4})
        page.wait_for_timeout(200)
        assert dialog.is_visible()

    def test_the_create_and_edit_dialogs_do_not_read_each_others_fields(
        self, types_page, live_server
    ):
        """Both hold a form with the same element ids and the closed one stays in
        the DOM, so reading `#tf-name` by id alone found the create form and
        posted a new type instead of updating one."""
        page, _ = types_page

        page.click("#new-type")
        create = page.locator("#newTypeModal")
        create.wait_for(state="visible")
        create.locator("#tf-name").fill("Moldura")
        create.locator("[data-dialog-submit]").click()
        create.wait_for(state="hidden")

        page.wait_for_selector("#type-rows tr")
        page.locator("#type-rows tr", has_text="Moldura").first.click()
        edit = page.locator("#editTypeModal")
        edit.wait_for(state="visible")

        assert edit.locator("#tf-name").input_value() == "Moldura"
        edit.locator("#tf-name").fill("Moldura grande")
        edit.locator("[data-dialog-submit]").click()
        edit.wait_for(state="hidden")

        body = page.request.get(f"{live_server}/api/product-types/").json()
        names = [t["name"] for t in body["product_types"]]
        assert names == ["Moldura grande"], "an update must not create a second row"

    def test_a_failed_submit_says_so_and_keeps_the_dialog_open(
        self, types_page, make_product_type
    ):
        """Losing what was typed because the name is taken is the worst possible
        answer, so `submitting` reports and stays put."""
        page, _ = types_page
        make_product_type("Caixa")   # the name the dialog is about to collide with
        page.reload()
        page.wait_for_selector("#new-type")

        page.click("#new-type")
        dialog = page.locator("#newTypeModal")
        dialog.wait_for(state="visible")
        dialog.locator("#tf-name").fill("Caixa")
        dialog.locator("[data-dialog-submit]").click()
        page.wait_for_selector(".swal2-container")

        assert dialog.is_visible()
        assert dialog.locator("#tf-name").input_value() == "Caixa"
        assert not dialog.locator("[data-dialog-submit]").evaluate(
            "button => button.classList.contains('is-loading')"
        ), "the spinner has to come off, or the button is dead for good"

    def test_confirm_runs_the_action_and_cancel_does_not(
        self, types_page, live_server
    ):
        page, _ = types_page
        page.click("#new-type")
        create = page.locator("#newTypeModal")
        create.wait_for(state="visible")
        create.locator("#tf-name").fill("Bastidor")
        create.locator("[data-dialog-submit]").click()
        create.wait_for(state="hidden")
        page.wait_for_selector("#type-rows tr")

        row = page.locator("#type-rows tr", has_text="Bastidor").first
        row.locator('[data-type-action="delete"]').click()
        confirm = page.locator("#deleteTypeModal")
        confirm.wait_for(state="visible")

        confirm.locator("[data-modal-close]").first.click()
        confirm.wait_for(state="hidden")
        body = page.request.get(f"{live_server}/api/product-types/").json()
        assert body["pagination"]["total"] == 1, "cancel must delete nothing"

        row.locator('[data-type-action="delete"]').click()
        confirm.wait_for(state="visible")
        assert "is-danger" in confirm.locator("[data-dialog-confirm]").get_attribute(
            "class"
        )
        confirm.locator("[data-dialog-confirm]").click()
        confirm.wait_for(state="hidden")

        body = page.request.get(f"{live_server}/api/product-types/").json()
        assert body["pagination"]["total"] == 0
