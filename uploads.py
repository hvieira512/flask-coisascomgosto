"""Storing uploaded product photographs on disk.

Files land in static/img/products/ and are served as ordinary static assets, so
`url` on a product image is the same whether the file arrived through an upload
or was placed there by hand.
"""

import secrets
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

# This module sits at the project root, so its own directory is that root.
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / "static" / "img" / "products"
URL_PREFIX = "/static/img/products"

# Collection covers live apart from the pieces on purpose. Replacing a cover
# should delete the file it replaced, and that is only safe while the folder says
# who owns it — a cover pointed at a product photograph must never take that
# photograph with it when the owners change their minds.
COLLECTION_DIR = PROJECT_ROOT / "static" / "img" / "collections"
COLLECTION_PREFIX = "/static/img/collections"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 5 * 1024 * 1024

# What the file turns out to actually be, and the suffix it is then stored under.
# The uploaded name only gets a say in whether we bother decoding at all.
FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

# A 5 MB file can still decode to an enormous bitmap, and decoding happens before
# anything else can judge it. These are photographs of small handmade objects; 40
# megapixels is already more than any of them, and well under Pillow's own default
# of ~89M, which is a lot of memory to hand a stranger.
Image.MAX_IMAGE_PIXELS = 40_000_000

# JPEG re-encoding would soften a photograph on every upload. "keep" reuses the
# source's own quantization tables, so the pixels come out as they went in.
SAVE_OPTIONS = {"JPEG": {"quality": "keep"}, "WEBP": {"quality": 90}}


class UploadError(ValueError):
    """The file was missing, the wrong type, or too large."""


def _extension(filename: str) -> str:
    return Path(secure_filename(filename or "")).suffix.lower()


def save(file_storage, *, folder=None, url_prefix=None) -> str:
    """Write an uploaded photograph and return the URL it is served from.

    `folder` and `url_prefix` default to the product folder and are read at call
    time, which is also what lets the tests point them somewhere disposable.

    The stored name is derived from the original but suffixed with random hex:
    two photographs called "caixa.jpg" must not overwrite one another, and the
    name reaches us from the browser, so it is never trusted as a path.

    The bytes are decoded rather than taken at their word. An extension proves
    nothing — the file is whatever the browser said it was called — so the image
    is opened, and the format it really is decides the suffix it is stored under.

    Re-encoding is also what strips the metadata: Pillow only writes EXIF when it
    is handed some, so saving a decoded image drops it. That matters because the
    owners photograph their work at home with a phone, and a phone writes the
    coordinates of the room into the file.
    """
    folder = folder or UPLOAD_DIR
    url_prefix = url_prefix or URL_PREFIX

    if file_storage is None or not file_storage.filename:
        raise UploadError("Nenhum ficheiro enviado.")

    extension = _extension(file_storage.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadError(
            f"Formato não suportado ({extension or 'sem extensão'}). "
            f"Use {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # Measure by seeking rather than reading the whole thing into memory, and
    # before decoding: the cheapest rejection should come first.
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise UploadError("O ficheiro está vazio.")
    if size > MAX_BYTES:
        raise UploadError(f"Máximo {MAX_BYTES // (1024 * 1024)} MB.")

    try:
        image = Image.open(file_storage.stream)
        # open() only reads the header. load() decodes, which is what catches a
        # file that is truncated or lying about its dimensions — better here than
        # halfway through writing it to disk.
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise UploadError("O ficheiro não é uma imagem válida.") from None

    if image.format not in FORMAT_EXTENSIONS:
        raise UploadError(
            f"Formato não suportado ({image.format or 'desconhecido'}). "
            f"Use {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    stem = Path(secure_filename(file_storage.filename)).stem[:40] or "foto"
    name = f"{stem}-{secrets.token_hex(4)}{FORMAT_EXTENSIONS[image.format]}"

    folder.mkdir(parents=True, exist_ok=True)
    image.save(folder / name, **SAVE_OPTIONS.get(image.format, {}))

    return f"{url_prefix}/{name}"


def delete_many(urls) -> None:
    """Remove the files behind rows that have just been deleted.

    The repositories hand back the URLs whose rows they removed; a URL that was
    never an upload of ours is ignored by `delete`, so seeded assets and
    hand-written paths survive a cascade the same way they survive a single delete.
    """
    for url in urls or ():
        delete(url)


def delete_cover(url: Optional[str]) -> None:
    """Remove a collection cover, and only ever one stored *as* a cover.

    A collection with no cover passes None, which is why the body tests the URL
    before looking at it — the annotation said `str` and the callers were passing
    exactly that None.

    A cover may be pointed at any URL, including one of the pieces' own
    photographs. Replacing it then reaches `delete`, which knows how to remove
    files from the product folder too — so without this narrowing, changing a
    collection's cover would delete a photograph a product row still points at.
    """
    if url and url.startswith(f"{COLLECTION_PREFIX}/"):
        delete(url)


def delete(url: Optional[str]) -> None:
    """Remove a previously uploaded file, ignoring anything outside our folders.

    Rows may point at files that were never uploaded — seeded assets, or a
    hand-written path — so a miss is not an error. A URL under neither prefix is
    left alone entirely, which is what stops a collection cover set to some other
    page's image from deleting it.
    """
    if not url:
        return

    for folder, prefix in ((UPLOAD_DIR, URL_PREFIX), (COLLECTION_DIR, COLLECTION_PREFIX)):
        if not url.startswith(f"{prefix}/"):
            continue

        path = (folder / Path(url).name).resolve()
        if path.parent == folder.resolve() and path.is_file():
            path.unlink()
        return
