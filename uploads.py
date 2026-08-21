"""Storing uploaded product photographs on disk.

Files land in static/img/products/ and are served as ordinary static assets, so
`url` on a product image is the same whether the file arrived through an upload
or was placed there by hand.

Nothing here deletes a file except `sweep`, which is reached only from
`flask sweep-uploads`. Removing a photograph in the dashboard marks its row;
deleting a piece removes rows. The photographs themselves outlive both, because
the only copy of one may be the one the owners uploaded.
"""

import secrets
import time
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

# This module sits at the project root, so its own directory is that root.
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / "static" / "img" / "products"
URL_PREFIX = "/static/img/products"

# Collection covers live apart from the pieces on purpose: a cover may be pointed
# at any URL, including one of the pieces' own photographs, and keeping the two
# folders separate is what lets the sweep tell a cover nobody uses any more from a
# photograph a product row still points at.
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


def sweep(
    referenced: set[str], *, older_than_days: int = 30, dry_run: bool = False
) -> list[str]:
    """Delete the files no row points at any more. The only unlink in the project.

    Nothing else removes a file. Deleting a photograph marks its row and leaves
    the file; deleting a piece or a colour takes the rows with it and leaves the
    files; replacing a collection cover leaves the one it replaced. All of it
    ends up here, which means a mis-tap costs nothing until somebody runs
    `flask sweep-uploads`, and even then only after a grace period.

    `referenced` is every URL the database still holds, removed photographs
    included — a removed one is restorable, so its file is still in use.

    The age check is on the file's own mtime, not on any row: an upload whose
    request failed after the file was written has no row at all, and deleting it
    the moment it appears would race a request that is still running.

    `dry_run` reports what would go without touching anything. It is a flag here
    rather than a second pass in the caller, so there is one rule about what is
    collectable instead of two that can drift.
    """
    cutoff = time.time() - older_than_days * 86_400
    removed = []

    for folder, prefix in ((UPLOAD_DIR, URL_PREFIX), (COLLECTION_DIR, COLLECTION_PREFIX)):
        if not folder.is_dir():
            continue

        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            if f"{prefix}/{path.name}" in referenced:
                continue
            if path.stat().st_mtime > cutoff:
                continue

            if not dry_run:
                path.unlink()
            removed.append(f"{prefix}/{path.name}")

    return removed
