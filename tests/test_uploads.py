"""Uploading product photographs.

`client` is signed in; `anon_client` is not.
"""

import io
import pathlib

import pytest

from PIL import Image

import uploads


def image_bytes(fmt="JPEG", size=(40, 30), exif=None, **save_options):
    """A real image, because the uploader decodes what it is given.

    These tests used to post b"\\xff\\xd8\\xff\\xe0 fake jpeg" and pass, which was
    the hole: fourteen bytes of nothing called foto.jpg went to disk and became a
    product photograph.
    """
    buffer = io.BytesIO()
    options = dict(save_options)
    if exif is not None:
        options["exif"] = exif
    Image.new("RGB", size, (120, 40, 60)).save(buffer, fmt, **options)
    return buffer.getvalue()


def phone_exif():
    """What a phone attaches: the make, and where the picture was taken."""
    exif = Image.Exif()
    exif[0x010F] = "TestPhone"
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (41.69, 8.83, 0.0)
    return exif


JPEG_BYTES = image_bytes()


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
def product(client, make_product, make_color, make_color_set):
    """A product with one colour on it.

    The colour is part of the fixture because every photograph belongs to one: a
    piece with no colours cannot be photographed at all.
    """
    created = make_product("Caixa")
    color_set = make_color_set("Branco", [make_color("Branco", hex="#F5F3EF")["id"]])
    variant = client.post(
        f"/api/products/{created['id']}/variants",
        json={"color_set_id": color_set["id"]},
    )
    assert variant.status_code == 201, variant.get_json()
    return {**created, "variant_id": variant.get_json()["id"]}


def upload(test_client, product, files, **form):
    """POST a photograph. `variant_id` defaults to the product's own colour, so a
    test only names one when the colour is what it is about."""
    form.setdefault("variant_id", str(product["variant_id"]))

    return test_client.post(
        f"/api/products/{product['id']}/images/upload",
        data={**files, **form},
        content_type="multipart/form-data",
    )


class TestUploadEndpoint:
    def test_requires_a_token(self, anon_client, product, photo):
        assert upload(anon_client, product, photo()).status_code == 401

    def test_stores_the_file_and_attaches_it(self, client, product, photo):
        response = upload(client, product, photo())
        assert response.status_code == 201

        body = response.get_json()
        assert body["url"].startswith("/static/img/products/")
        assert (uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name).is_file()

    def test_rejects_a_non_image(self, client, product, photo):
        response = upload(client, product, photo(name="notas.txt"))
        assert response.status_code == 400
        assert "suportado" in response.get_json()["message"]

    def test_rejects_an_oversized_file(self, client, product, photo):
        big = photo(data=b"x" * (uploads.MAX_BYTES + 1))
        assert upload(client, product, big).status_code == 400

    def test_unknown_product_is_404(self, client, photo):
        assert upload(
            client, {"id": 9999, "variant_id": 1}, photo()
        ).status_code == 404

    def test_can_be_pinned_to_a_variant(self, client, product, photo,
                                        make_color, make_color_set):
        color = make_color("Vermelho", hex="#B3282D")
        color_set = make_color_set("Vermelho", [color["id"]])
        variant = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()

        response = upload(client, product, photo(),
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

        response = upload(client, product, photo(),
                          variant_id=str(variant["id"]))
        assert response.status_code == 404

    def test_deleting_the_image_removes_the_file(self, client, product, photo):
        created = upload(client, product, photo()).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        assert path.is_file()

        client.delete(f"/api/products/{product['id']}/images/{created['id']}")
        assert not path.exists()


class TestACascadeTakesTheFilesWithIt:
    """Every path that deletes an image row has to delete the file behind it.

    Only the images endpoint did. Deleting a piece, dropping one of its colours, or
    deleting a colour set removed the rows and left the photographs on disk — which
    is where orphaned uploads come from, and 120 of them were deleted in 86d6b0b.
    """

    @pytest.fixture()
    def variant(self, client, product, make_color, make_color_set):
        color = make_color("Vermelho", hex="#B3282D")
        color_set = make_color_set("Vermelho", [color["id"]])
        created = client.post(
            f"/api/products/{product['id']}/variants",
            json={"color_set_id": color_set["id"]},
        ).get_json()
        return created, color_set

    def _photo_of(self, client, product, photo, **form):
        created = upload(client, product, photo(), **form).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        assert path.is_file()
        return path

    def test_deleting_the_piece_removes_its_photographs(self, client, product, photo):
        product_photo = self._photo_of(client, product, photo)

        client.delete(f"/api/products/{product['id']}")
        assert not product_photo.exists()

    def test_deleting_the_piece_removes_its_colours_photographs(
        self, client, product, photo, variant
    ):
        created, _ = variant
        pinned = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )

        client.delete(f"/api/products/{product['id']}")
        assert not pinned.exists()

    def test_dropping_a_colour_removes_that_colours_photographs(
        self, client, product, photo, variant
    ):
        created, _ = variant
        pinned = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )
        kept = self._photo_of(client, product, photo)

        client.delete(f"/api/products/{product['id']}/variants/{created['id']}")

        assert not pinned.exists()
        assert kept.is_file(), "another colour's photograph is not this colour's"

    def test_deleting_a_colour_set_removes_the_photographs_of_its_variants(
        self, client, product, photo, variant
    ):
        """The colour set cascades to every variant offered in it, wherever they are."""
        created, color_set = variant
        pinned = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )

        client.delete(f"/api/color-sets/{color_set['id']}")
        assert not pinned.exists()

    def test_a_photograph_it_did_not_upload_is_left_alone(self, client, product):
        """A row may point at a seeded asset or a path written by hand."""
        attached = client.post(
            f"/api/products/{product['id']}/images",
            json={
                "url": "/static/img/logo.png",
                "variant_id": product["variant_id"],
            },
        )
        # Without this the row is never created and the assertion below passes
        # for the wrong reason — nothing referenced the file to begin with.
        assert attached.status_code == 201, attached.get_json()

        client.delete(f"/api/products/{product['id']}")
        assert (uploads.PROJECT_ROOT / "static" / "img" / "logo.png").is_file()


class TestFilenameSafety:
    """The name arrives from the browser, so it is never trusted as a path."""

    def test_traversal_is_stripped(self, client, product):
        body = upload(client, product,
                      {"file": (io.BytesIO(JPEG_BYTES), "../../../evil.jpg")}).get_json()

        stored = pathlib.Path(body["url"])
        assert ".." not in body["url"]
        assert stored.parent.as_posix() == "/static/img/products"
        assert (uploads.UPLOAD_DIR / stored.name).is_file()

    def test_two_uploads_of_one_name_do_not_collide(self, client, product):
        urls = {
            upload(client, product,
                   {"file": (io.BytesIO(JPEG_BYTES), "caixa.jpg")}).get_json()["url"]
            for _ in range(2)
        }
        assert len(urls) == 2


class TestWhatIsActuallyInTheFile:
    """An extension is a claim by whoever uploaded the file, so the bytes decide.

    Nothing here was covered before: the uploader trusted the suffix and wrote the
    stream straight to disk.
    """

    def test_a_file_that_is_not_an_image_is_refused(self, client, product):
        """The old fixture — fourteen bytes with a JPEG magic number — went
        through, and every page then rendered an <img> pointing at rubbish."""
        response = upload(client, product,
                          {"file": (io.BytesIO(b"\xff\xd8\xff\xe0 fake jpeg"), "foto.jpg")})

        assert response.status_code == 400
        assert "não é uma imagem" in response.get_json()["message"]
        assert list(uploads.UPLOAD_DIR.iterdir()) == [], "nothing may reach the disk"

    def test_a_truncated_image_is_refused(self, client, product):
        """A cut-off upload has a perfectly good header."""
        whole = image_bytes(size=(200, 200))
        response = upload(client, product,
                          {"file": (io.BytesIO(whole[: len(whole) // 3]), "foto.jpg")})

        assert response.status_code == 400
        assert list(uploads.UPLOAD_DIR.iterdir()) == []

    def test_the_stored_suffix_follows_the_real_format(self, client, product):
        """A PNG named .jpg is stored as .png, because the suffix is what the
        browser will be told the file is when it is served back."""
        body = upload(client, product,
                      {"file": (io.BytesIO(image_bytes("PNG")), "enganador.jpg")}).get_json()

        assert body["url"].endswith(".png")
        stored = uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name
        assert Image.open(stored).format == "PNG"

    def test_an_svg_dressed_as_a_png_is_refused(self, client, product):
        """The one that matters: markup with a .png suffix, which Pillow cannot
        open and which a browser would otherwise be free to interpret."""
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        response = upload(client, product, {"file": (io.BytesIO(svg), "foto.png")})

        assert response.status_code == 400
        assert list(uploads.UPLOAD_DIR.iterdir()) == []


class TestMetadataIsStripped:
    """The owners photograph their work at home, and a phone writes the
    coordinates of the room into the file. Those files are then served publicly.
    """

    def test_exif_does_not_reach_the_disk(self, client, product):
        original = image_bytes(exif=phone_exif())
        assert Image.open(io.BytesIO(original)).getexif(), "the fixture must carry EXIF"

        body = upload(client, product,
                      {"file": (io.BytesIO(original), "foto.jpg")}).get_json()

        stored = Image.open(uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name)
        assert dict(stored.getexif()) == {}
        assert stored.info.get("exif") is None

    def test_the_gps_tag_in_particular_is_gone(self, client, product):
        body = upload(client, product,
                      {"file": (io.BytesIO(image_bytes(exif=phone_exif())), "foto.jpg")}).get_json()

        stored = Image.open(uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name)
        assert 0x8825 not in dict(stored.getexif())

    def test_the_photograph_itself_survives(self, client, product):
        """Stripping must not quietly re-encode the picture into mush: JPEG is
        saved with the source's own quantization tables."""
        body = upload(client, product,
                      {"file": (io.BytesIO(image_bytes(size=(64, 48))), "foto.jpg")}).get_json()

        stored = Image.open(uploads.UPLOAD_DIR / pathlib.Path(body["url"]).name)
        assert stored.size == (64, 48)
        assert stored.format == "JPEG"


class TestDecompressionLimit:
    def test_a_bomb_is_refused_rather_than_decoded(self, client, product, monkeypatch):
        """A few hundred kilobytes of PNG can decode to gigabytes of bitmap, and
        decoding is the first thing that happens to it."""
        monkeypatch.setattr(uploads.Image, "MAX_IMAGE_PIXELS", 1000)

        response = upload(client, product,
                          {"file": (io.BytesIO(image_bytes("PNG", size=(400, 400))), "foto.png")})

        assert response.status_code == 400
        assert list(uploads.UPLOAD_DIR.iterdir()) == []


class TestDeleteHelper:
    def test_ignores_paths_outside_the_upload_folder(self):
        """Seeded assets and hand-written paths survive a row deletion."""
        uploads.delete("/static/img/logo.png")
        assert (uploads.PROJECT_ROOT / "static" / "img" / "logo.png").is_file()

    def test_ignores_a_missing_file(self):
        uploads.delete("/static/img/products/nao-existe.jpg")
