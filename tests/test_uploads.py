"""Uploading product photographs.

`client` is signed in; `anon_client` is not.
"""

import io
import pathlib

import pytest

from api import uploads

JPEG_BYTES = b"\xff\xd8\xff\xe0 fake jpeg"


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    """Write uploads somewhere disposable.

    Without this the suite files real photographs into static/img/products/ and
    only the two deletion tests clean up after themselves, so every run left a
    handful of orphans behind in the repository.
    """
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def photo():
    def _make(name="foto.jpg", data=JPEG_BYTES):
        return {"file": (io.BytesIO(data), name)}

    return _make


@pytest.fixture()
def product(make_product):
    return make_product("Caixa")


def upload(test_client, product_id, files, **form):
    return test_client.post(
        f"/api/products/{product_id}/images/upload",
        data={**files, **form},
        content_type="multipart/form-data",
    )


class TestUploadEndpoint:
    def test_requires_a_token(self, anon_client, product, photo):
        assert upload(anon_client, product["id"], photo()).status_code == 401

    def test_stores_the_file_and_attaches_it(self, client, product, photo):
        response = upload(client, product["id"], photo())
        assert response.status_code == 201

        body = response.get_json()
        assert body["url"].startswith("/static/img/products/")
        assert (uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name).is_file()

    def test_rejects_a_non_image(self, client, product, photo):
        response = upload(client, product["id"], photo(name="notas.txt"))
        assert response.status_code == 400
        assert "suportado" in response.get_json()["message"]

    def test_rejects_an_oversized_file(self, client, product, photo):
        big = photo(data=b"x" * (uploads.MAX_BYTES + 1))
        assert upload(client, product["id"], big).status_code == 400

    def test_unknown_product_is_404(self, client, photo):
        assert upload(client, 9999, photo()).status_code == 404

    def test_can_be_pinned_to_a_variant(self, client, product, photo,
                                        make_color, make_color_set):
        color = make_color("Vermelho", hex="#B3282D")
        color_set = make_color_set("Vermelho", [color["id"]])
        variant = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()

        response = upload(client, product["id"], photo(),
                          variant_id=str(variant["id"]))
        assert response.status_code == 201
        assert response.get_json()["variant_id"] == variant["id"]

    def test_a_variant_of_another_product_is_404(self, client, product, photo,
                                                 make_product, make_color,
                                                 make_color_set):
        other = make_product("Outra")
        color = make_color("Azul", hex="#2C5FA8")
        color_set = make_color_set("Azul", [color["id"]])
        variant = client.post(
            f"/api/products/{other['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()

        response = upload(client, product["id"], photo(),
                          variant_id=str(variant["id"]))
        assert response.status_code == 404

    def test_deleting_the_image_removes_the_file(self, client, product, photo):
        created = upload(client, product["id"], photo()).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        assert path.is_file()

        client.delete(f"/api/products/{product['id']}/images/{created['id']}")
        assert not path.exists()


class TestFilenameSafety:
    """The name arrives from the browser, so it is never trusted as a path."""

    def test_traversal_is_stripped(self, client, product):
        body = upload(client, product["id"],
                      {"file": (io.BytesIO(JPEG_BYTES), "../../../evil.jpg")}).get_json()

        stored = pathlib.Path(body["url"])
        assert ".." not in body["url"]
        assert stored.parent.as_posix() == "/static/img/products"
        assert (uploads.UPLOAD_DIR / stored.name).is_file()

    def test_two_uploads_of_one_name_do_not_collide(self, client, product):
        urls = {
            upload(client, product["id"],
                   {"file": (io.BytesIO(JPEG_BYTES), "caixa.jpg")}).get_json()["url"]
            for _ in range(2)
        }
        assert len(urls) == 2


class TestDeleteHelper:
    def test_ignores_paths_outside_the_upload_folder(self):
        """Seeded assets and hand-written paths survive a row deletion."""
        uploads.delete("/static/img/logo.png")
        assert (uploads.PROJECT_ROOT / "static" / "img" / "logo.png").is_file()

    def test_ignores_a_missing_file(self):
        uploads.delete("/static/img/products/nao-existe.jpg")
