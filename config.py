import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT", 25)
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
