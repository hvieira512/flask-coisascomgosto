"""Editing a collection, in a real browser.

This exists because the behaviour below was guarded by a test that grepped the
JavaScript for the line `payload.image_url = collection.image_url`. That passes
whether the form works or not, and fails whenever the line moves — so it was
protecting the spelling rather than the collection's cover.

`live_server` and `browser` come from conftest.py.
"""

import io
import json

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def collections_page(browser, live_server, client, make_user, make_collection):
    """A collection with a cover, on the collections page, signed in."""
    from tests.test_uploads import image_bytes

    make_user("dash", password="Passw0rd!")
    collection = make_collection("Filigrana", description="Volutas e corações")

    cover = client.post(
        f"/api/collections/{collection['id']}/cover",
        data={"file": (io.BytesIO(image_bytes()), "capa.jpg")},
        content_type="multipart/form-data",
    )
    assert cover.status_code == 201, cover.get_json()
    covered = cover.get_json()
    assert covered["image_url"]

    context = browser.new_context(viewport={"width": 1280, "height": 950})
    context.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "dash", "password": "Passw0rd!"}),
        headers={"Content-Type": "application/json"},
    )
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.goto(f"{live_server}/dashboard/collections")
    page.wait_for_selector("#collection-rows tr[data-collection-id]")

    yield page, errors, covered
    context.close()


class TestRenamingKeepsTheCover:
    """PUT replaces the row, so a form that does not send image_url clears a cover
    the owner never touched — and the cover is the collection's whole presence on
    the catalogue's front page."""

    def test_the_cover_survives_an_edit(self, collections_page, client):
        page, errors, collection = collections_page

        page.locator("#collection-rows tr[data-collection-id]").first.click()
        page.wait_for_selector("#editCollectionModal.show")
        name = page.locator("#editCollectionModal input#cof-name")
        name.fill("Filigrana de Viana")
        page.locator("#editCollectionModal [data-dialog-submit]").click()
        page.wait_for_selector("#editCollectionModal.show", state="hidden")

        after = client.get("/api/collections/").get_json()["collections"][0]
        assert after["name"] == "Filigrana de Viana"
        assert after["image_url"] == collection["image_url"], "the edit lost the cover"
        assert errors == []

    def test_the_row_still_shows_the_cover_afterwards(self, collections_page):
        page, _, _ = collections_page

        page.locator("#collection-rows tr[data-collection-id]").first.click()
        page.wait_for_selector("#editCollectionModal.show")
        page.locator("#editCollectionModal input#cof-name").fill("Outro nome")
        page.locator("#editCollectionModal [data-dialog-submit]").click()
        page.wait_for_selector("#editCollectionModal.show", state="hidden")
        page.wait_for_selector("#collection-rows tr[data-collection-id]")

        thumbnail = page.locator("#collection-rows .dash-thumb")
        assert thumbnail.count() == 1
        assert page.locator("#collection-rows", has_text="Sem capa").count() == 0
