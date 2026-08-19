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


def _fill_identity(dialog, name="Caixa Redonda"):
    """The first step's two required answers."""
    dialog.locator('[name="name"]').fill(name)
    dialog.locator('[name="type_id"]').select_option(label="Caixa")


def _to_the_end(dialog):
    """Walk from wherever the wizard is to the button that writes."""
    while dialog.locator("[data-step-next]").inner_text().strip() == "Continuar":
        dialog.locator("[data-step-next]").click()
    dialog.locator("[data-step-next]").click()


def _write_photo(tmp_path, name):
    """A real JPEG on disk, since the uploader decodes what it is given."""
    from tests.test_uploads import image_bytes

    path = tmp_path / name
    path.write_bytes(image_bytes())
    return path


def _put_photo(scope, tmp_path, name):
    """Choose a photograph in `scope`'s empty slot, the way the file dialog would."""
    scope.locator('.photo-slot:not(.is-filled) input[type="file"]').set_input_files(
        str(_write_photo(tmp_path, name))
    )


def _filled(scope):
    return scope.locator(".photo-slot.is-filled").count()


def _drop_photo(page, slot, name):
    """Drop a photograph onto a slot, which no file input can stand in for."""
    slot.evaluate(
        """(element, name) => {
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = 8;
            return new Promise((resolve) => {
                canvas.toBlob((blob) => {
                    const transfer = new DataTransfer();
                    transfer.items.add(new File([blob], name, { type: 'image/png' }));
                    const event = new DragEvent('drop', { bubbles: true, cancelable: true });
                    Object.defineProperty(event, 'dataTransfer', { value: transfer });
                    element.dispatchEvent(event);
                    resolve();
                }, 'image/png');
            });
        }""",
        name,
    )


class TestStepDialog:
    """core/steps.js, driven the way an owner drives it."""

    def test_it_opens_on_the_first_step_with_no_way_back(self, products_page):
        page, errors = products_page
        dialog = _open_wizard(page)

        assert "Passo 1 de 3" in dialog.locator("[data-step-label]").text_content()
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
        assert "Passo 1 de 3" in dialog.locator("[data-step-label]").text_content()

        # A name but no type still is not enough.
        dialog.locator('[name="name"]').fill("Caixa Redonda")
        dialog.locator("[data-step-next]").click()
        page.wait_for_timeout(300)
        assert "tipo é obrigatório" in page.locator(".swal2-container").inner_text()
        assert "Passo 1 de 3" in dialog.locator("[data-step-label]").text_content()

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

        assert "Passo 2 de 3" in dialog.locator("[data-step-label]").text_content()
        assert dialog.locator("[data-step-progress]").get_attribute("value") == "2"
        assert not dialog.locator('[name="name"]').is_visible()
        assert dialog.locator('[name="description"]').is_visible()
        assert dialog.locator("[data-step-back]").is_visible()
        assert dialog.locator("[data-step-next]").inner_text().strip() == "Continuar"

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
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()
        assert product_count() == 0, "reaching the last step must not create it"

        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        assert product_count() == 0, "abandoning the wizard must not create it"

    def test_the_last_step_writes_once_and_hands_over_to_the_photographs(
        self, products_page, live_server
    ):
        """The colours are chosen in the wizard now, so photographs are what is
        left: the only thing that needs both an id and a file."""
        page, errors = products_page
        dialog = _open_wizard(page)

        _fill_identity(dialog)
        _to_the_end(dialog)

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")

        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["pagination"]["total"] == 1
        assert body["products"][0]["name"] == "Caixa Redonda"

        # Landing on Detalhes would show the owner the form they just filled.
        assert edit.locator("#edit-tabs li.is-active").inner_text().strip() == (
            "Cores e fotografias"
        )
        assert edit.locator('[data-panel="variants"]').is_visible()
        assert not edit.locator('[data-panel="details"]').is_visible()
        assert errors == []

    def test_editing_shows_both_groups_at_once(self, products_page, live_server):
        """Editing is changing one thing, so it is not a sequence: both groups are
        on screen and there is no step chrome."""
        page, _ = products_page
        dialog = _open_wizard(page)

        _fill_identity(dialog)
        _to_the_end(dialog)

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")
        edit.locator('#edit-tabs [data-tab="details"]').click()

        assert edit.locator('[name="name"]').is_visible()
        assert edit.locator('[name="description"]').is_visible()
        assert edit.locator("[data-step-label]").count() == 0


class TestChoosingColoursWhileCreating:
    """The colours a piece is offered in, chosen in the wizard rather than after it.

    A variant needs a product id, so the choice is held in the page and posted once
    the product exists. That must not weaken the wizard's promise: until the last
    button, nothing at all is written.
    """

    @pytest.fixture()
    def with_colour_sets(self, products_page, make_color_set, make_color):
        white = make_color("Branco", hex="#FFFFFF")
        gold = make_color("Dourado", hex="#C8A24B")
        black = make_color("Preto", hex="#111111")
        sets = {
            "Branco e Dourado": make_color_set(
                "Branco e Dourado", color_ids=[white["id"], gold["id"]]),
            "Preto e Dourado": make_color_set(
                "Preto e Dourado", color_ids=[black["id"], gold["id"]]),
        }
        page, errors = products_page
        page.reload()
        page.wait_for_selector("#new-product")
        return page, errors, sets

    def test_the_third_step_offers_every_colour_set(self, with_colour_sets):
        page, errors, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        assert "Passo 3 de 3" in dialog.locator("[data-step-label]").text_content()
        assert dialog.locator(".variant-choice").count() == 2
        assert dialog.locator("[data-step-next]").inner_text().strip() == "Criar produto"
        assert errors == []

    def test_choosing_none_is_allowed(self, with_colour_sets, live_server):
        """A piece may be made in one colour, or its colours decided later."""
        page, _, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        _to_the_end(dialog)
        page.locator("#editProductModal").wait_for(state="visible")

        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["products"][0]["variants"] == []

    def test_the_chosen_colours_are_attached_to_the_new_piece(
        self, with_colour_sets, live_server
    ):
        page, errors, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()
        dialog.locator("[data-step-next]").click()
        page.locator("#editProductModal").wait_for(state="visible")

        body = page.request.get(f"{live_server}/api/products/").json()
        names = sorted(v["color_set"]["name"] for v in body["products"][0]["variants"])
        assert names == ["Branco e Dourado", "Preto e Dourado"]
        assert errors == []

    def test_a_chip_can_be_unchosen(self, with_colour_sets, live_server):
        page, _, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        chip = dialog.locator(".variant-choice", has_text="Branco e Dourado")
        chip.click()
        assert chip.get_attribute("aria-pressed") == "true"
        chip.click()
        assert chip.get_attribute("aria-pressed") == "false"

        dialog.locator("[data-step-next]").click()
        page.locator("#editProductModal").wait_for(state="visible")
        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["products"][0]["variants"] == []

    def test_choosing_colours_writes_nothing_before_the_last_button(
        self, with_colour_sets, live_server
    ):
        page, _, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()
        dialog.locator(".variant-choice").first.click()

        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["pagination"]["total"] == 0, "picking a colour created the piece"

        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["pagination"]["total"] == 0

    def _at_the_colour_step(self, page):
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()
        return dialog

    def test_a_photo_slot_appears_only_for_the_colours_chosen(self, with_colour_sets):
        """The dialog grows with the answer, not with the list: nine colour sets
        must not mean nine file pickers."""
        page, errors, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        assert not dialog.locator("#variant-photos").is_visible()

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        assert dialog.locator("#variant-photos").is_visible()
        assert dialog.locator("[data-photo-for]").count() == 1

        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()
        assert dialog.locator("[data-photo-for]").count() == 2

        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()
        assert dialog.locator("[data-photo-for]").count() == 1
        assert errors == []

    def test_a_photo_chosen_for_one_colour_survives_ticking_another(
        self, with_colour_sets, tmp_path
    ):
        """A tray redrawn from scratch would lose the files it holds, so the rows are
        moved rather than rebuilt when the chips change."""
        page, _, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        _put_photo(dialog.locator("[data-photo-for]").first, tmp_path, "caixa.jpg")
        assert _filled(dialog) == 1

        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()
        assert dialog.locator("[data-photo-for]").count() == 2
        assert _filled(dialog) == 1, "the held photograph was lost"
        assert _filled(dialog.locator("[data-photo-for]").first) == 1

    def test_a_colour_can_hold_several_photographs(self, with_colour_sets, tmp_path):
        """A variant may be photographed more than once, so the tray keeps an empty
        slot after the filled ones."""
        page, _, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        row = dialog.locator("[data-photo-for]").first

        _put_photo(row, tmp_path, "uma.jpg")
        _put_photo(row, tmp_path, "outra.jpg")

        assert _filled(row) == 2
        assert row.locator(".photo-slot:not(.is-filled)").count() == 1

    def test_the_photo_can_be_taken_back(self, with_colour_sets, tmp_path):
        """Clicking the photograph removes it — the whole area, not just the ×."""
        page, _, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        row = dialog.locator("[data-photo-for]").first
        _put_photo(row, tmp_path, "caixa.jpg")

        row.locator(".photo-slot.is-filled").click()

        assert _filled(row) == 0
        assert row.locator(".photo-slot").count() == 1

    def test_the_photo_lands_on_its_own_variant(
        self, with_colour_sets, live_server, tmp_path
    ):
        """The whole point: a photograph chosen for Branco e Dourado has to arrive
        pinned to that variant, not to the piece as a whole or to the other colour."""
        page, errors, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()
        # The second row's tray: the first colour deliberately gets no photograph.
        _put_photo(dialog.locator("[data-photo-for]").nth(1), tmp_path, "preto.jpg")

        dialog.locator("[data-step-next]").click()
        page.locator("#editProductModal").wait_for(state="visible")

        product = page.request.get(f"{live_server}/api/products/").json()["products"][0]
        by_set = {v["color_set"]["name"]: v for v in product["variants"]}
        assert [i["url"] for i in by_set["Branco e Dourado"]["images"]] == []
        assert len(by_set["Preto e Dourado"]["images"]) == 1
        assert by_set["Preto e Dourado"]["images"][0]["url"].endswith(".jpg")
        assert errors == []

    def test_unticking_a_colour_drops_its_photo_too(
        self, with_colour_sets, live_server, tmp_path
    ):
        """Otherwise the upload arrives for a variant the piece does not have."""
        page, _, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        _put_photo(dialog.locator("[data-photo-for]").first, tmp_path, "caixa.jpg")
        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        dialog.locator(".variant-choice", has_text="Preto e Dourado").click()

        dialog.locator("[data-step-next]").click()
        page.locator("#editProductModal").wait_for(state="visible")

        product = page.request.get(f"{live_server}/api/products/").json()["products"][0]
        assert [v["color_set"]["name"] for v in product["variants"]] == ["Preto e Dourado"]
        assert product["variants"][0]["images"] == []

    def test_a_photo_writes_nothing_before_the_last_button(
        self, with_colour_sets, live_server, tmp_path
    ):
        page, _, _ = with_colour_sets
        dialog = self._at_the_colour_step(page)

        dialog.locator(".variant-choice", has_text="Branco e Dourado").click()
        _put_photo(dialog.locator("[data-photo-for]").first, tmp_path, "caixa.jpg")

        body = page.request.get(f"{live_server}/api/products/").json()
        assert body["pagination"]["total"] == 0, "choosing a photograph created the piece"

    def test_the_selected_ring_is_not_hidden_behind_the_badge(self, with_colour_sets):
        """The chip is only a wrapper — the badge inside brings its own background,
        and an inset shadow would paint beneath it, which is exactly how the ring
        went missing on the storefront's collection cards."""
        page, _, _ = with_colour_sets
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()

        chip = dialog.locator(".variant-choice").first
        before = chip.bounding_box()
        chip.click()
        after = chip.bounding_box()

        assert chip.evaluate("el => getComputedStyle(el).boxShadow") == "none"
        assert chip.evaluate("el => getComputedStyle(el).borderTopWidth") == "2px"
        assert (round(before["width"]), round(before["height"])) == (
            round(after["width"]), round(after["height"])
        ), "choosing a colour resized the chip"


class TestThePhotoPicker:
    """core/photo-picker.js: the area a photograph is dropped, chosen or shot into.

    Driven through the create wizard's colour step, which is one of its callers, so
    the component is exercised where it actually runs rather than on a scratch page.
    """

    @pytest.fixture()
    def slot(self, products_page, make_color, make_color_set, tmp_path):
        color = make_color("Branco", hex="#FFFFFF")
        make_color_set("Branco e Dourado", color_ids=[color["id"]])

        page, errors = products_page
        page.reload()
        page.wait_for_selector("#new-product")

        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()
        dialog.locator(".variant-choice").first.click()
        return page, dialog.locator("[data-photo-for]").first, errors

    def test_the_empty_state_invites_all_three_ways_in(self, slot):
        """Drop, choose, or take one: one input covers the last two — accept for the
        file dialog, capture for a phone's camera — and the slot itself takes drops."""
        _, row, errors = slot
        empty = row.locator(".photo-slot")

        assert empty.locator(".photo-slot-icon .fa-camera").count() == 1
        assert empty.locator('input[type="file"]').get_attribute("capture") == "environment"
        assert "image/jpeg" in empty.locator('input[type="file"]').get_attribute("accept")
        assert errors == []

    def test_the_input_is_hidden_but_still_reachable_by_keyboard(self, slot):
        """display: none would take it out of the tab order and the picker would be
        mouse-only; the slot lights up through :focus-within instead."""
        _, row, _ = slot
        state = row.locator('.photo-slot input[type="file"]').evaluate(
            """el => {
                const style = getComputedStyle(el);
                return { display: style.display, opacity: style.opacity };
            }"""
        )
        assert state["display"] != "none"
        assert state["opacity"] == "0"

    def test_a_chosen_photograph_fills_the_area(self, slot, tmp_path):
        page, row, _ = slot
        _put_photo(row, tmp_path, "caixa.jpg")

        filled = row.locator(".photo-slot.is-filled")
        # Against the slot's inner box: bounding_box() includes the 2px border, which
        # the image sits inside rather than under.
        fills = filled.evaluate(
            """el => {
                const image = el.querySelector('img').getBoundingClientRect();
                return Math.abs(image.width - el.clientWidth) < 1
                    && Math.abs(image.height - el.clientHeight) < 1;
            }"""
        )
        assert fills, "the photograph does not fill its slot"
        assert filled.locator("img").evaluate("el => getComputedStyle(el).objectFit") == "cover"
        assert filled.locator("img").get_attribute("src").startswith("blob:")

    def test_the_border_goes_solid_once_it_holds_something(self, slot, tmp_path):
        """Dashed says "put something here"; it has something now."""
        _, row, _ = slot
        assert row.locator(".photo-slot").evaluate(
            "el => getComputedStyle(el).borderTopStyle"
        ) == "dashed"

        _put_photo(row, tmp_path, "caixa.jpg")
        assert row.locator(".photo-slot.is-filled").evaluate(
            "el => getComputedStyle(el).borderTopStyle"
        ) == "solid"

    def test_the_cross_appears_on_hover_and_the_whole_area_removes(self, slot, tmp_path):
        page, row, _ = slot
        _put_photo(row, tmp_path, "caixa.jpg")
        filled = row.locator(".photo-slot.is-filled")

        assert filled.locator(".photo-slot-x").evaluate(
            "el => getComputedStyle(el).opacity"
        ) == "0"

        filled.hover()
        page.wait_for_function(
            """() => getComputedStyle(
                document.querySelector('.photo-slot.is-filled .photo-slot-x')).opacity === '1'"""
        )

        # Not the × itself: clicking anywhere in the area takes the photograph back.
        filled.click(position={"x": 8, "y": 40})
        assert _filled(row) == 0

    def test_dropping_over_a_filled_slot_replaces_what_is_there(self, slot, tmp_path):
        """The one way to swap a photograph, since clicking removes it."""
        page, row, _ = slot
        _put_photo(row, tmp_path, "primeira.jpg")
        first = row.locator(".photo-slot.is-filled img").get_attribute("src")

        _drop_photo(page, row.locator(".photo-slot.is-filled"), "segunda.jpg")

        assert _filled(row) == 1, "the drop added a slot instead of replacing"
        assert row.locator(".photo-slot.is-filled img").get_attribute("src") != first

    def test_dragging_over_it_says_so(self, slot):
        page, row, _ = slot
        empty = row.locator(".photo-slot")

        page.evaluate(
            """() => {
                const slot = document.querySelector('.photo-slot');
                const event = new DragEvent('dragover', { bubbles: true, cancelable: true });
                Object.defineProperty(event, 'dataTransfer', { value: new DataTransfer() });
                slot.dispatchEvent(event);
            }"""
        )
        assert "is-over" in empty.get_attribute("class")

    def test_a_file_that_is_not_an_image_is_refused_before_any_upload(
        self, slot, tmp_path
    ):
        """The server checks too. Refusing here means the owner is not told after
        watching an upload finish."""
        page, row, _ = slot
        notes = tmp_path / "notas.txt"
        notes.write_text("nada")

        row.locator('.photo-slot input[type="file"]').set_input_files(str(notes))
        page.wait_for_selector(".swal2-container")

        assert "não é uma imagem" in page.locator(".swal2-container").inner_text()
        assert _filled(row) == 0

    def test_a_file_over_five_megabytes_is_refused(self, slot, tmp_path):
        page, row, _ = slot
        heavy = tmp_path / "grande.jpg"
        heavy.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * (5 * 1024 * 1024))

        row.locator('.photo-slot input[type="file"]').set_input_files(str(heavy))
        page.wait_for_selector(".swal2-container")

        assert "MB" in page.locator(".swal2-container").inner_text()
        assert _filled(row) == 0


class TestTheCollectionFormIsSplit:
    """The fields on one side, the cover on the other — and stacked on a phone."""

    def _open(self, page, live_server):
        page.goto(f"{live_server}/dashboard/collections")
        page.wait_for_selector("#new-collection")
        page.click("#new-collection")
        dialog = page.locator("#newCollectionModal")
        dialog.wait_for(state="visible")
        return dialog

    def test_the_cover_sits_beside_the_fields(self, signed_in, live_server):
        page, errors = signed_in
        dialog = self._open(page, live_server)

        name = dialog.locator("#cof-name").bounding_box()
        cover = dialog.locator("#cof-cover .photo-slot").bounding_box()

        assert cover["x"] > name["x"] + name["width"], "the cover is not to the right"
        assert abs(cover["y"] - name["y"]) < 40, "they are not on the same row"
        assert errors == []

    def test_it_stacks_on_a_phone(self, browser, live_server, make_user):
        """Bulma's columns stack below 769px, so the cover follows the fields rather
        than being squeezed into a third of a phone screen."""
        make_user("phone", password="Passw0rd!")
        context = browser.new_context(viewport={"width": 390, "height": 780})
        context.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "phone", "password": "Passw0rd!"}),
            headers={"Content-Type": "application/json"},
        )
        page = context.new_page()
        page.set_default_timeout(5000)
        try:
            dialog = self._open(page, live_server)

            name = dialog.locator("#cof-name").bounding_box()
            cover = dialog.locator("#cof-cover .photo-slot").bounding_box()

            assert cover["y"] > name["y"] + name["height"], "still side by side at 390px"
            assert not page.evaluate(
                "() => document.documentElement.scrollWidth > window.innerWidth"
            )
        finally:
            context.close()

    def test_the_dialog_does_not_have_to_be_scrolled_to_reach_the_cover(
        self, signed_in, live_server
    ):
        """The point of the split: both halves are visible at once."""
        page, _ = signed_in
        dialog = self._open(page, live_server)

        assert not dialog.locator(".modal-card-body").evaluate(
            "el => el.scrollHeight > el.clientHeight + 1"
        )


class TestChoosingACollectionsColourSets:
    """The collections form says which colour sets are the collection's own.

    The relationship lived only at the other end before: a colour set could name a
    collection, and a collection could not take one.
    """

    @pytest.fixture()
    def form(self, signed_in, live_server, client, make_collection, make_color,
             make_color_set):
        white = make_color("Branco", hex="#FFFFFF")
        blue = make_color("Azul", hex="#2C5FA8")
        filigrana = make_collection("Filigrana")
        bordados = make_collection("Bordados")

        mine = make_color_set("Branco e Dourado", color_ids=[white["id"]])
        theirs = make_color_set("Branco e Azul", color_ids=[blue["id"]])
        free = make_color_set("Preto e Branco", color_ids=[white["id"]])
        client.put(
            f"/api/collections/{filigrana['id']}/color-sets",
            json={"color_set_ids": [mine["id"]]},
        )
        client.put(
            f"/api/collections/{bordados['id']}/color-sets",
            json={"color_set_ids": [theirs["id"]]},
        )

        page, errors = signed_in
        page.goto(f"{live_server}/dashboard/collections")
        page.wait_for_selector("#collection-rows tr")
        page.locator("#collection-rows tr", has_text="Filigrana").first.click()
        dialog = page.locator("#editCollectionModal")
        dialog.wait_for(state="visible")
        page.wait_for_selector("#cof-sets .variant-choice")
        return page, dialog, errors, {"mine": mine, "theirs": theirs, "free": free}

    def _chip(self, dialog, name):
        return dialog.locator(".variant-choice", has_text=name).first

    def test_every_colour_set_is_offered(self, form):
        page, dialog, errors, _ = form
        names = dialog.locator("#cof-sets .variant-choice").all_text_contents()

        assert sorted(n.strip() for n in names) == [
            "Branco e Azul", "Branco e Dourado", "Preto e Branco"
        ]
        assert errors == []

    def test_the_collections_own_are_already_chosen(self, form):
        _, dialog, _, _ = form
        assert self._chip(dialog, "Branco e Dourado").get_attribute("aria-pressed") == "true"
        assert self._chip(dialog, "Preto e Branco").get_attribute("aria-pressed") == "false"

    def test_one_that_belongs_elsewhere_says_where(self, form):
        """Choosing it would take it from that collection, so the form says so."""
        _, dialog, _, _ = form
        assert self._chip(dialog, "Branco e Azul").get_attribute("title") == "Está em Bordados"

    def test_the_collections_own_come_first(self, form):
        _, dialog, _, _ = form
        names = [
            n.strip()
            for n in dialog.locator("#cof-sets .variant-choice").all_text_contents()
        ]
        assert names[0] == "Branco e Dourado"

    def test_choosing_one_assigns_it_on_save(self, form, live_server):
        page, dialog, _, ids = form
        self._chip(dialog, "Preto e Branco").click()
        dialog.locator("[data-dialog-submit]").click()
        dialog.wait_for(state="hidden")

        page.wait_for_function(
            """async () => {
                const body = await fetch('/api/color-sets/?limit=100').then(r => r.json());
                const set = body.color_sets.find(s => s.name === 'Preto e Branco');
                return set.collection && set.collection.name === 'Filigrana';
            }"""
        )

    def test_unchoosing_one_leaves_it_belonging_to_none(self, form, live_server):
        page, dialog, _, _ = form
        self._chip(dialog, "Branco e Dourado").click()
        dialog.locator("[data-dialog-submit]").click()
        dialog.wait_for(state="hidden")

        page.wait_for_function(
            """async () => {
                const body = await fetch('/api/color-sets/?limit=100').then(r => r.json());
                const set = body.color_sets.find(s => s.name === 'Branco e Dourado');
                return set.collection === null;
            }"""
        )

    def test_the_ring_is_not_mistaken_for_the_badges_own_border(self, form):
        """A colour set's badge carries a 1px border in its own colour. A blue set's
        looked exactly like the chosen ring pressed against it, so the chip keeps a
        gap — and the ring is a border rather than an inset shadow, which the badge
        would paint over."""
        _, dialog, _, _ = form
        chip = self._chip(dialog, "Branco e Dourado")

        style = chip.evaluate(
            """el => {
                const s = getComputedStyle(el);
                return { padding: s.paddingTop, shadow: s.boxShadow, width: s.borderTopWidth };
            }"""
        )
        assert style["shadow"] == "none"
        assert style["width"] == "2px"
        assert int(style["padding"].replace("px", "")) >= 2

    def test_choosing_does_not_move_the_chip(self, form):
        page, dialog, _, _ = form
        # The dialog scales in over .18s, so a box measured too early is a
        # transformed one: this read 131x33 opening and 133x34 settled, and blamed
        # the click.
        page.wait_for_function(
            "() => document.getElementById('editCollectionModal').getAnimations().length === 0"
        )

        chip = self._chip(dialog, "Preto e Branco")
        before = chip.bounding_box()
        chip.click()
        after = chip.bounding_box()

        assert (round(before["width"]), round(before["height"])) == (
            round(after["width"]), round(after["height"])
        )


class TestColoursAndPhotographsAreOnePanel:
    """Two tabs became one.

    A photograph belongs to a colour, so a tab of colours beside a tab of photographs
    was the same fact twice — and the photographs tab had to name the colour again in a
    dropdown, with a "Todas as cores (fallback)" option for a photograph of no colour
    at all, which is not a thing the shop can describe.
    """

    @pytest.fixture()
    def photos_tab(self, products_page, make_color, make_color_set):
        color = make_color("Branco", hex="#FFFFFF")
        make_color_set("Branco e Dourado", color_ids=[color["id"]])

        page, errors = products_page
        page.reload()
        page.wait_for_selector("#new-product")
        return page, errors

    def _open_colours(self, page, colours=True):
        """Create a piece, optionally with a colour, and land on its Cores panel."""
        dialog = _open_wizard(page)
        _fill_identity(dialog)
        dialog.locator("[data-step-next]").click()
        dialog.locator("[data-step-next]").click()
        if colours:
            dialog.locator(".variant-choice").first.click()
        dialog.locator("[data-step-next]").click()

        edit = page.locator("#editProductModal")
        edit.wait_for(state="visible")
        return edit

    def test_there_is_no_photographs_tab(self, photos_tab):
        page, errors = photos_tab
        edit = self._open_colours(page)

        tabs = [t.strip() for t in edit.locator("#edit-tabs li").all_text_contents()]
        assert tabs == ["Detalhes", "Cores e fotografias"]
        assert edit.locator('[data-panel="images"]').count() == 0
        assert errors == []

    def test_each_colour_carries_its_own_photographs(self, photos_tab):
        """One tray per colour, in the row that names the colour — so nothing has to
        ask which colour a photograph belongs to."""
        page, _ = photos_tab
        edit = self._open_colours(page)

        row = edit.locator("[data-variant-block]")
        assert row.count() == 1
        assert row.locator(".photo-slot").count() >= 1
        assert row.locator("[data-remove-variant]").count() == 1

    def test_a_piece_with_no_colours_says_what_to_do(self, photos_tab):
        page, _ = photos_tab
        edit = self._open_colours(page, colours=False)

        panel = edit.locator('[data-panel="variants"]')
        assert panel.locator("[data-variant-block]").count() == 0
        assert panel.locator(".photo-slot").count() == 0, (
            "nowhere to put a photograph until there is a colour to put it in"
        )
        assert "Sem cores associadas" in panel.inner_text()

    def test_uploading_refuses_a_photograph_with_no_colour(self, photos_tab):
        """Belt as well as braces: the panel cannot ask for one, and the function
        behind it will not do it either."""
        page, _ = photos_tab
        self._open_colours(page)

        refusal = page.evaluate(
            """async () => {
                const module = await import('/static/js/dashboard/products/images.js');
                try {
                    await module.uploadImage(1, { file: new File(['x'], 'a.jpg') });
                    return null;
                } catch (error) {
                    return error.message;
                }
            }"""
        )
        assert refusal and "cor" in refusal, refusal


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
