import os
from datetime import timedelta

from dotenv import load_dotenv

# Must run before the class body below, which reads the environment at import
# time. load_dotenv never overwrites a variable that is already set, so real
# environment variables — the ones docker compose injects — still win.
load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT", 25)
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # ----------------
    # JWT
    # ----------------
    # Falls back to SECRET_KEY so a dev install works out of the box; set
    # JWT_SECRET_KEY explicitly in production so rotating one does not
    # invalidate the other.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

    # Short-lived access token, long-lived refresh token: the client keeps
    # working for a fortnight without re-entering a password, and a leaked
    # access token expires quickly.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTES", 15))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", 14))
    )

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
