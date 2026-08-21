"""Uploading product photographs.

`client` is signed in; `anon_client` is not.
"""

import io
import os
import pathlib
import time

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

    def test_deleting_the_image_leaves_the_file(self, client, product, photo):
        """It used to unlink it here. See TestNoDeletionTouchesAFile."""
        created = upload(client, product, photo()).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        assert path.is_file()

        client.delete(f"/api/products/{product['id']}/images/{created['id']}")
        assert path.is_file()


class TestNoDeletionTouchesAFile:
    """The photographs outlive every delete.

    They used to be unlinked in the same request: removing one photograph,
    dropping a colour, deleting a piece or replacing a collection cover all took
    the file with them. For people whose only copy of a photograph may be the one
    they uploaded from a phone, a mis-tap was unrecoverable — and a confirmation
    naming the count is not a backup.

    Now nothing deletes a file except uploads.sweep(), reached only from
    `flask sweep-uploads`, and only after a grace period.
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
        return created, path

    def test_removing_a_photograph_keeps_the_file(self, client, product, photo):
        created, path = self._photo_of(client, product, photo)

        response = client.delete(
            f"/api/products/{product['id']}/images/{created['id']}"
        )

        assert response.status_code == 200
        assert path.is_file(), "the photograph was deleted from disk"

    def test_removing_a_photograph_takes_it_out_of_the_catalogue(
        self, client, product, photo
    ):
        """Kept on disk, and kept out of sight: it must not come back on the
        product page because the row survived."""
        created, _ = self._photo_of(client, product, photo)

        client.delete(f"/api/products/{product['id']}/images/{created['id']}")

        listed = client.get(f"/api/products/{product['id']}/images").get_json()
        body = client.get(f"/api/products/{product['id']}").get_json()
        assert listed == []
        assert body["primary_image"] is None
        assert body["variants"][0]["images"] == []

    def test_a_removed_photograph_cannot_be_removed_twice(self, client, product, photo):
        created, _ = self._photo_of(client, product, photo)
        client.delete(f"/api/products/{product['id']}/images/{created['id']}")

        again = client.delete(f"/api/products/{product['id']}/images/{created['id']}")

        assert again.status_code == 404

    def test_it_can_be_put_back(self, client, product, photo):
        """Which is the point of keeping the row. There is no button for it yet —
        one UPDATE is the whole recovery.

        Its own connection rather than the `cursor` fixture: that one holds a
        transaction open for the whole test, and MySQL's REPEATABLE READ keeps the
        snapshot it started with, so it cannot see what the client committed."""
        from db import get_db_connection
        from repositories import ProductImageRepository

        created, _ = self._photo_of(client, product, photo)
        client.delete(f"/api/products/{product['id']}/images/{created['id']}")

        with get_db_connection() as (_, cursor):
            ProductImageRepository(cursor).restore(created["id"])

        listed = client.get(f"/api/products/{product['id']}/images").get_json()
        assert [image["id"] for image in listed] == [created["id"]]

    def test_deleting_the_piece_keeps_its_photographs(self, client, product, photo):
        _, path = self._photo_of(client, product, photo)

        client.delete(f"/api/products/{product['id']}")

        assert path.is_file()

    def test_dropping_a_colour_keeps_its_photographs(
        self, client, product, photo, variant
    ):
        created, _ = variant
        _, path = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )

        client.delete(f"/api/products/{product['id']}/variants/{created['id']}")

        assert path.is_file()

    def test_deleting_a_colour_set_keeps_the_photographs(
        self, client, product, photo, variant
    ):
        created, color_set = variant
        _, path = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )

        client.delete(f"/api/color-sets/{color_set['id']}")

        assert path.is_file()

    def test_the_rows_still_go_when_the_colour_does(
        self, client, product, photo, variant
    ):
        """A soft-deleted photograph of a colour that no longer exists is a state
        nothing could present, so those rows are removed outright. Only the file
        survives."""
        created, _ = variant
        image, _ = self._photo_of(
            client, product, photo, variant_id=str(created["id"])
        )

        client.delete(f"/api/products/{product['id']}/variants/{created['id']}")

        assert client.get(
            f"/api/products/{product['id']}/images"
        ).get_json() == []
        assert image["id"]


class TestTheSweepIsTheOnlyThingThatDeletes:
    """`flask sweep-uploads` removes files nothing points at, once they are old
    enough. Age is read off the file rather than off a row, because an upload
    whose request failed after the file was written has no row at all — and
    collecting it the instant it appears would race a request still running."""

    def _file(self, name="orfa.jpg", age_days=0):
        path = uploads.UPLOAD_DIR / name
        path.write_bytes(JPEG_BYTES)
        if age_days:
            old = time.time() - age_days * 86_400
            os.utime(path, (old, old))
        return path

    def test_it_removes_a_file_no_row_points_at(self):
        path = self._file(age_days=40)

        removed = uploads.sweep(set(), older_than_days=30)

        assert not path.exists()
        assert removed == [f"{uploads.URL_PREFIX}/{path.name}"]

    def test_it_leaves_a_referenced_file_however_old(self):
        path = self._file(age_days=400)

        uploads.sweep({f"{uploads.URL_PREFIX}/{path.name}"}, older_than_days=30)

        assert path.is_file()

    def test_it_leaves_a_file_inside_the_grace_period(self):
        """A photograph uploaded a moment ago has no row yet for the length of the
        request that is storing it."""
        path = self._file(age_days=1)

        uploads.sweep(set(), older_than_days=30)

        assert path.is_file()

    def test_a_dry_run_changes_nothing(self):
        path = self._file(age_days=40)

        reported = uploads.sweep(set(), older_than_days=30, dry_run=True)

        assert reported == [f"{uploads.URL_PREFIX}/{path.name}"]
        assert path.is_file(), "a dry run deleted the file"

    def test_a_removed_photograph_is_referenced_until_its_row_is_purged(
        self, client, product, photo
    ):
        """This is what makes removal reversible: the row keeps the file alive."""
        from db import get_db_connection
        from repositories import ProductImageRepository

        created = upload(client, product, photo()).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        client.delete(f"/api/products/{product['id']}/images/{created['id']}")
        old = time.time() - 400 * 86_400
        os.utime(path, (old, old))

        with get_db_connection() as (_, cursor):
            referenced = ProductImageRepository(cursor).referenced_urls()
        uploads.sweep(referenced, older_than_days=30)

        assert path.is_file()

    def test_purging_the_row_first_is_what_frees_the_file(
        self, client, product, photo
    ):
        from db import get_db_connection
        from repositories import ProductImageRepository

        created = upload(client, product, photo()).get_json()
        path = uploads.UPLOAD_DIR / pathlib.Path(created["url"]).name
        client.delete(f"/api/products/{product['id']}/images/{created['id']}")
        old = time.time() - 400 * 86_400
        os.utime(path, (old, old))

        with get_db_connection() as (_, cursor):
            images = ProductImageRepository(cursor)
            # Marked a moment ago, so nothing to purge yet at thirty days.
            assert images.purge_deleted(older_than_days=30) == 0
            # Everything marked, however recently.
            assert images.purge_deleted(older_than_days=0) == 1
            referenced = images.referenced_urls()

        uploads.sweep(referenced, older_than_days=30)

        assert not path.exists()

    def test_a_seeded_asset_is_not_in_the_upload_folder_at_all(self):
        """Rows may point at files placed by hand. The sweep only ever looks inside
        the two upload folders, so those cannot be collected."""
        uploads.sweep(set(), older_than_days=0)

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
