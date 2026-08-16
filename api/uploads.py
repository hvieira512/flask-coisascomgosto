"""Storing uploaded product photographs on disk.

Files land in static/img/products/ and are served as ordinary static assets, so
`url` on a product image is the same whether the file arrived through an upload
or was placed there by hand.
"""

import secrets
from pathlib import Path

from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "static" / "img" / "products"
URL_PREFIX = "/static/img/products"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 5 * 1024 * 1024


class UploadError(ValueError):
    """The file was missing, the wrong type, or too large."""


def _extension(filename: str) -> str:
    return Path(secure_filename(filename or "")).suffix.lower()


def save(file_storage) -> str:
    """Write an uploaded photograph and return the URL it is served from.

    The stored name is derived from the original but suffixed with random hex:
    two photographs called "caixa.jpg" must not overwrite one another, and the
    name reaches us from the browser, so it is never trusted as a path.
    """
    if file_storage is None or not file_storage.filename:
        raise UploadError("Nenhum ficheiro enviado.")

    extension = _extension(file_storage.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadError(
            f"Formato não suportado ({extension or 'sem extensão'}). "
            f"Use {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # Measure by seeking rather than reading the whole thing into memory.
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise UploadError("O ficheiro está vazio.")
    if size > MAX_BYTES:
        raise UploadError(f"Máximo {MAX_BYTES // (1024 * 1024)} MB.")

    stem = Path(secure_filename(file_storage.filename)).stem[:40] or "foto"
    name = f"{stem}-{secrets.token_hex(4)}{extension}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_storage.save(UPLOAD_DIR / name)

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
