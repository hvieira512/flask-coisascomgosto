"""Shared fixtures.

The suite runs against a real MySQL server, so dialect-specific SQL is actually
exercised. The schema is created once per session, then every table is
truncated and the seeds replayed before each test — which also resets
AUTO_INCREMENT, so IDs start at 1 every time.
"""

import os

import pytest
from dotenv import load_dotenv

# Before anything imports config, which reads MYSQL_DATABASE at import time.
# init_db() drops every table, so a stray environment variable must never be
# able to point the suite at the real database.
load_dotenv()
_name = os.environ.get("MYSQL_DATABASE", "coisascomgosto")
if not _name.endswith("_test"):
    os.environ["MYSQL_DATABASE"] = f"{_name}_test"


@pytest.fixture(scope="session")
def database():
    from api.db import init_db

    init_db()
    return os.environ["MYSQL_DATABASE"]


@pytest.fixture(autouse=True)
def clean_database(database):
    """Empty every table and replay the schema seeds before each test."""
    from api.db import SCHEMA_PATH, _statements, get_db_connection

    seeds = [s for s in _statements(SCHEMA_PATH.read_text())
             if s.upper().startswith("INSERT")]

    with get_db_connection() as (_, cursor):
        cursor.execute(
            "SELECT table_name AS name FROM information_schema.tables "
            "WHERE table_schema = %s",
            (database,),
        )
        tables = [row["name"] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"TRUNCATE TABLE `{table}`")
        for statement in seeds:
            cursor.execute(statement)


@pytest.fixture()
def app(clean_database):
    """A Flask app bound to the freshly emptied test database."""
    from app import app as flask_app

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        # 32+ bytes, or PyJWT warns the HMAC key is too short for SHA256.
        JWT_SECRET_KEY="test-jwt-secret-key-at-least-32-bytes-long",
    )
    return flask_app


@pytest.fixture()
def anon_client(app):
    """A client carrying no token. Use it to prove an endpoint is guarded."""
    return app.test_client()


@pytest.fixture()
def client(anon_client, tokens):
    """The default client, authenticated.

    Catalog writes require a bearer token, so the ordinary client carries one —
    the same way the dashboard does. Tests that assert a guard rejects an
    anonymous caller ask for `anon_client` instead.
    """
    return _AuthorizedClient(
        anon_client, {"Authorization": f"Bearer {tokens['access_token']}"}
    )


class _AuthorizedClient:
    """Test client that attaches a bearer token to every request.

    Lets a protected endpoint be exercised without repeating `headers=` at
    each call site.
    """

    def __init__(self, client, headers):
        self._client = client
        self._headers = headers

    def _with_auth(self, kwargs):
        """Attach the token, unless the caller supplied its own.

        The refresh endpoint needs the refresh token, not the access token, so
        an explicit Authorization header always wins.
        """
        headers = dict(kwargs.pop("headers", {}) or {})
        for name, value in self._headers.items():
            headers.setdefault(name, value)
        kwargs["headers"] = headers
        return kwargs

    def get(self, *args, **kwargs):
        return self._client.get(*args, **self._with_auth(kwargs))

    def post(self, *args, **kwargs):
        return self._client.post(*args, **self._with_auth(kwargs))

    def put(self, *args, **kwargs):
        return self._client.put(*args, **self._with_auth(kwargs))

    def delete(self, *args, **kwargs):
        return self._client.delete(*args, **self._with_auth(kwargs))

    def session_transaction(self, *args, **kwargs):
        return self._client.session_transaction(*args, **kwargs)


@pytest.fixture()
def tokens(anon_client, make_user):
    """Register a user and return their freshly issued token pair."""
    make_user("tokenuser", password="Passw0rd!")

    response = anon_client.post(
        "/api/auth/login", json={"username": "tokenuser", "password": "Passw0rd!"}
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


@pytest.fixture()
def auth_client(client):
    """Kept as a name: the default client is already authenticated."""
    return client


@pytest.fixture()
def cursor(app):
    """A live cursor against the test database, for repository unit tests."""
    from api.db import get_db_connection

    with get_db_connection() as (_, cur):
        yield cur


@pytest.fixture()
def make_category(client):
    def _make(name="Bebidas"):
        response = client.post("/api/categories/", json={"name": name})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def make_product(client, make_category):
    default_category = {}

    def _make(
        name="Vinho",
        description="Tinto",
        category_id=None,
        type_id=None,
        collection_id=None,
        default_size_id=None,
    ):
        if category_id is None:
            # Reuse one default category so repeated calls don't collide on
            # the categories.name unique constraint.
            if "id" not in default_category:
                default_category.update(make_category())
            category_id = default_category["id"]

        payload = {
            "name": name,
            "description": description,
            "category_id": category_id,
        }
        for key, value in (
            ("type_id", type_id),
            ("collection_id", collection_id),
            ("default_size_id", default_size_id),
        ):
            if value is not None:
                payload[key] = value

        response = client.post("/api/products/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def make_collection(client):
    def _make(name="Barra da Saia", description=None):
        payload = {"name": name}
        if description is not None:
            payload["description"] = description
        response = client.post("/api/collections/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def make_color(client):
    def _make(name="White", hex=None):
        payload = {"name": name}
        if hex is not None:
            payload["hex"] = hex
        response = client.post("/api/colors/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def make_color_set(client, make_color):
    def _make(name="White and Green", color_ids=None, collection_id=None):
        if color_ids is None:
            color_ids = [make_color(f"{name} filler")["id"]]

        payload = {"name": name, "color_ids": color_ids}
        if collection_id is not None:
            payload["collection_id"] = collection_id

        response = client.post("/api/color-sets/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def make_product_type(client):
    def _make(name="Coracao", parent_id=None, description=None, icon=None):
        payload = {"name": name}
        if parent_id is not None:
            payload["parent_id"] = parent_id
        if description is not None:
            payload["description"] = description
        if icon is not None:
            payload["icon"] = icon
        response = client.post("/api/product-types/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def sizes(client):
    """The S / M / L rows seeded by the schema, keyed by name."""
    body = client.get("/api/sizes/").get_json()
    return {s["name"]: s for s in body["sizes"]}


@pytest.fixture()
def make_user(anon_client):
    def _make(username="alice", email=None, password="Passw0rd!"):
        response = anon_client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email or f"{username}@example.com",
                "password": password,
            },
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make
