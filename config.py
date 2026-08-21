import os
from datetime import timedelta

from dotenv import load_dotenv

from uploads import MAX_BYTES

load_dotenv()

DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

# The values .env.example ships — one per key, so both belong here. They are in
# the repository, so a deployment running on either signs its session cookies or
# its JWTs with a public constant, and anyone could forge a dashboard session and
# rewrite the catalogue.
_DEV_SECRET = "dev-secret-change-me"
_PLACEHOLDERS = frozenset({_DEV_SECRET, "dev-jwt-secret-change-me"})


def _secret(name: str, default: str) -> str:
    """A signing key, or a refusal to start without one.

    Loud rather than convenient: the failure this prevents is silent, and a
    deployment that boots normally with a known key looks exactly like a
    deployment that is safe.
    """
    value = os.getenv(name, default)
    if value in _PLACEHOLDERS and not DEBUG:
        raise RuntimeError(
            f"{name} still holds the development value from .env.example, so "
            "cookies and tokens would be signed with a key that is public. Set "
            "it to a real secret before starting outside FLASK_DEBUG=1."
        )
    return value


class Config:
    DEBUG = DEBUG

    # SECRET_KEY signs the dashboard's session cookie; JWT_SECRET_KEY signs the
    # API's bearer tokens. Neither has a usable default in production.
    SECRET_KEY = _secret("SECRET_KEY", _DEV_SECRET)
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", 15)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", 14)))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # The session cookie is a credential: api/security.py accepts it in place of
    # a bearer token, so it can write to the whole catalogue.
    #
    # Lax rather than Strict: every dashboard request that carries it is a
    # same-site fetch, and Strict would additionally drop the cookie when the
    # owners arrive from a link in their mail — a logout they did not ask for.
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    # No cookie over plain HTTP, except in development, where there is no TLS to
    # send it over.
    SESSION_COOKIE_SECURE = not DEBUG
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # Werkzeug refuses a larger body with 413 before anything reads it.
    # uploads.MAX_BYTES is still the check that matters — it answers in
    # Portuguese and names the file — but it runs after the upload has arrived,
    # so this is what stops a 2GB POST being buffered first. Read from uploads
    # rather than repeated, so the two cannot drift; the margin covers the
    # multipart envelope around a photograph of the maximum size.
    MAX_CONTENT_LENGTH = MAX_BYTES + 1024 * 1024

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "coisascomgosto")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "coisascomgosto")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "coisascomgosto")
