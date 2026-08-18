"""Storing uploaded product photographs on disk.

Files land in static/img/products/ and are served as ordinary static assets, so
`url` on a product image is the same whether the file arrived through an upload
or was placed there by hand.
"""

import secrets
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

# This module sits at the project root, so its own directory is that root.
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / "static" / "img" / "products"
URL_PREFIX = "/static/img/products"

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


def save(file_storage) -> str:
    """Write an uploaded photograph and return the URL it is served from.

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

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    image.save(UPLOAD_DIR / name, **SAVE_OPTIONS.get(image.format, {}))

    return f"{URL_PREFIX}/{name}"


def delete(url: str) -> None:
    """Remove a previously uploaded file, ignoring anything outside the folder.

    Image rows may point at files that were never uploaded — seeded assets, or
    a hand-written path — so a miss is not an error.
    """
    if not url or not url.startswith(f"{URL_PREFIX}/"):
        return

    path = (UPLOAD_DIR / Path(url).name).resolve()
    if path.parent == UPLOAD_DIR.resolve() and path.is_file():
        path.unlink()
