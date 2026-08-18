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
    from db import init_db

    # The suite wants a blank slate; init_db otherwise carries accounts across a
    # schema rebuild, which is what keeps the owners logged in on a real database.
    init_db(keep_users=False)
    return os.environ["MYSQL_DATABASE"]


@pytest.fixture(autouse=True)
def clean_database(database):
    """Empty every table and replay the schema seeds before each test."""
    from db import SCHEMA_PATH, _statements, get_db_connection

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
            # schema_migrations is a record of the schema, not application data.
            # Emptying it between tests would say the migrations had never run
            # against a schema that already has them.
            if table == "schema_migrations":
                continue
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
    """A client with neither a token nor a session. Use it to prove an endpoint
    is guarded."""
    return app.test_client()


@pytest.fixture()
def client(app, make_user):
    """The default client, authenticated by session.

    A protected endpoint accepts either a bearer token or a session, and the
    session is the cheaper one to hold in a test: a test client keeps its cookies
    across requests the way a browser does, so signing in once is enough. Tests
    of the token path itself use the `tokens` fixture and pass the header
    explicitly. This is a client of its own, so `anon_client` stays anonymous
    even in a test that asks for both.
    """
    make_user("tokenuser", password="Passw0rd!")

    signed_in = app.test_client()
    response = signed_in.post(
        "/api/auth/login", json={"username": "tokenuser", "password": "Passw0rd!"}
    )
    assert response.status_code == 200, response.get_json()
    return signed_in


@pytest.fixture()
def tokens(app, make_user):
    """Register a user and return their freshly issued token pair.

    Logs in on a throwaway client, never on `anon_client`: login also sets the
    session cookie, so borrowing that client would leave it authenticated and
    every "a token is required here" test would pass on the cookie instead.
    """
    make_user("apiclient", password="Passw0rd!")

    response = app.test_client().post(
        "/api/auth/login", json={"username": "apiclient", "password": "Passw0rd!"}
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


@pytest.fixture()
def bearer(tokens):
    """The Authorization header an API client would send."""
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture()
def auth_client(client):
    """Kept as a name: the default client is already signed in."""
    return client


@pytest.fixture()
def cursor(app):
    """A live cursor against the test database, for repository unit tests."""
    from db import get_db_connection

    with get_db_connection() as (_, cur):
        yield cur


@pytest.fixture(scope="session")
def live_server(database):
    """The app on a real socket, in a thread, against the test database.

    Shared by the browser tests. Werkzeug rather than gunicorn: it only has to
    answer one browser, and port 0 lets the OS pick so a developer's own
    `flask run` is not in the way.
    """
    import threading

    from werkzeug.serving import make_server

    from app import app as flask_app

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        JWT_SECRET_KEY="test-jwt-secret-key-at-least-32-bytes-long",
    )

    server = make_server("127.0.0.1", 0, flask_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser():
    """One chromium for the whole session. Skips when it was never downloaded."""
    sync_api = pytest.importorskip("playwright.sync_api")

    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as error:  # the browser binary is not installed
            pytest.skip(f"chromium unavailable: {error}")
        yield instance
        instance.close()


@pytest.fixture()
def make_material(client):
    def _make(name="Madeira"):
        response = client.post("/api/materials/", json={"name": name})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def product_type(make_product_type):
    """A ready-made type, for tests that build a product payload by hand — a
    product cannot be created without one.

    Deliberately not a real domain name. product_types is utf8mb4_unicode_ci,
    which is accent-insensitive, so a default of "Coracao" collided with a test
    creating "Coração".
    """
    return make_product_type("Tipo de teste")


@pytest.fixture()
def make_product(client, product_type):
    def _make(
        name="Vinho",
        description="Tinto",
        type_id=None,
        material_id=None,
        collection_id=None,
        default_size_id=None,
    ):
        # A product must have a type. Both this and the `product_type` fixture
        # lean on the same one, so a test using each does not collide on the
        # sibling-name unique constraint.
        if type_id is None:
            type_id = product_type["id"]

        payload = {
            "name": name,
            "description": description,
            "type_id": type_id,
        }
        for key, value in (
            ("material_id", material_id),
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
    def _make(name="Coracao", description=None, icon=None):
        payload = {"name": name}
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
    """The Pequeno / Médio / Grande rows seeded by the schema, keyed by name."""
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
