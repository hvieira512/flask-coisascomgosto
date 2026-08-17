import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # Signs the session cookie, which is the whole of authentication.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "coisascomgosto")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "coisascomgosto")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "coisascomgosto")
