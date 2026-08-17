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

    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return flask_app


@pytest.fixture()
def anon_client(app):
    """A client that never signs in. Use it to prove an endpoint is guarded."""
    return app.test_client()


@pytest.fixture()
def client(app, make_user):
    """The default client, signed in.

    Writes require a session, so the ordinary client holds one. A test client
    keeps its cookies across requests the way a browser does, so signing in once
    is enough — and this is a client of its own, so `anon_client` stays signed
    out even in a test that asks for both.
    """
    make_user("tokenuser", password="Passw0rd!")

    signed_in = app.test_client()
    response = signed_in.post(
        "/api/auth/login", json={"username": "tokenuser", "password": "Passw0rd!"}
    )
    assert response.status_code == 200, response.get_json()
    return signed_in


@pytest.fixture()
def auth_client(client):
    """Kept as a name: the default client is already signed in."""
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
