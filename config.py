"""Every setting the application reads, in one place.

.env is loaded here and nowhere else. Real environment variables always win —
load_dotenv does not overwrite what is already set — which is how docker
compose overrides MYSQL_HOST inside the network.

Flask settings are resolved at import. Database settings are resolved per call,
because the test suite repoints MYSQL_DATABASE after this module is imported.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

DEV_SECRET = "dev-secret-change-me"
DEV_JWT_SECRET = "dev-jwt-secret-change-me"


def env(key: str, default=None) -> str:
    value = os.environ.get(key, default)
    return value.strip() if isinstance(value, str) else value


def env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{key} must be an integer, got {raw!r}") from None


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def database_config(*, database: bool = True) -> dict:
    """PyMySQL connection kwargs. `database=False` omits the schema name, which
    is how init_db connects before the database exists."""
    config = {
        "host": env("MYSQL_HOST", "127.0.0.1"),
        "port": env_int("MYSQL_PORT", 3306),
        "user": env("MYSQL_USER", "coisascomgosto"),
        "password": env("MYSQL_PASSWORD", "coisascomgosto"),
        "charset": "utf8mb4",
        "autocommit": False,
    }
    if database:
        config["database"] = database_name()
    return config


def database_name() -> str:
    return env("MYSQL_DATABASE", "coisascomgosto")


class Config:
    DEBUG = env_bool("FLASK_DEBUG")

    SECRET_KEY = env("SECRET_KEY", DEV_SECRET)
    # Falls back to SECRET_KEY so a dev install works out of the box; set both
    # in production so rotating one does not invalidate the other.
    JWT_SECRET_KEY = env("JWT_SECRET_KEY", SECRET_KEY)

    # Short-lived access token, long-lived refresh token: a leaked access token
    # expires quickly while the user stays signed in for a fortnight.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 15))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=env_int("JWT_REFRESH_DAYS", 14))

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    MAIL_SERVER = env("MAIL_SERVER")
    MAIL_PORT = env_int("MAIL_PORT", 25)
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS")
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL")
    MAIL_DEFAULT_SENDER = env("MAIL_DEFAULT_SENDER")


def check_production_secrets() -> None:
    """Refuse to serve real traffic with the committed development secrets."""
    if Config.DEBUG:
        return

    weak = [
        name
        for name, value, dev in (
            ("SECRET_KEY", Config.SECRET_KEY, DEV_SECRET),
            ("JWT_SECRET_KEY", Config.JWT_SECRET_KEY, DEV_JWT_SECRET),
        )
        if value == dev
    ]
    if weak:
        raise RuntimeError(
            f"{' and '.join(weak)} still set to the development default. "
            "Set a real value, or run with FLASK_DEBUG=1."
        )
