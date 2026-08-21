"""Tests for the session half of authentication.

The dashboard's pages are rendered server-side, so they cannot carry a token from
localStorage — they are gated by Flask's session cookie instead, and the API
guard accepts it alongside a bearer token. The token half is covered in
test_jwt_auth.py.
"""

from io import BytesIO

import pytest

GUARDED = [
    ("get", "/api/users/"),
    ("get", "/api/users/1"),
    ("get", "/api/contacts/"),
    ("get", "/api/auth/me"),
]


class TestSigningIn:
    def test_login_populates_the_session(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")
        anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        )

        with anon_client.session_transaction() as flask_session:
            assert flask_session["user"]["username"] == "alice"

    def test_bad_password_leaves_the_caller_anonymous(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        response = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )

        assert response.status_code == 401
        assert anon_client.get("/api/auth/me").status_code == 401

    def test_the_cookie_carries_across_requests(self, client):
        """One sign-in is enough; the dashboard attaches nothing per call."""
        assert client.get("/api/auth/me").status_code == 200
        assert client.get("/api/auth/me").status_code == 200

    def test_the_session_authorises_a_write(self, client):
        """This is what lets the dashboard's fetch() calls stay plain."""
        response = client.post("/api/materials/", json={"name": "Vidro"})
        assert response.status_code == 201


class TestGuards:
    @pytest.mark.parametrize("method,path", GUARDED)
    def test_signed_out_returns_401(self, anon_client, method, path):
        assert getattr(anon_client, method)(path).status_code == 401

    @pytest.mark.parametrize("method,path", GUARDED)
    def test_signed_in_is_allowed(self, auth_client, method, path):
        assert getattr(auth_client, method)(path).status_code != 401

    def test_a_session_wins_even_with_a_broken_token(self, client):
        """The guard checks the session first, so a client holding both is not
        locked out by a stale token."""
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert response.status_code == 200


class TestCrossSiteWritesCannotUseTheCookie:
    """The cookie is a credential the browser attaches to *any* request to this
    origin, including one a third-party page made. `X-Requested-With` is what
    separates our own code from that page: a cross-site HTML form cannot set a
    header at all, and a cross-site fetch() that sets one asks for a preflight
    this API does not answer.

    `csrf_client` is a signed-in client that sends no header — exactly what a
    request forged by another site looks like on the wire. It is a client of its
    own rather than the shared one stripped of its header, because the fixtures
    that create test records post through the shared one.
    """

    @pytest.fixture()
    def csrf_client(self, app, make_user):
        make_user("forged", password="Passw0rd!")
        attacker = app.test_client()
        response = attacker.post(
            "/api/auth/login", json={"username": "forged", "password": "Passw0rd!"}
        )
        assert response.status_code == 200, response.get_json()
        return attacker

    def test_a_json_write_without_the_header_is_refused(self, csrf_client):
        response = csrf_client.post("/api/materials/", json={"name": "Latão"})

        assert response.status_code == 403
        assert "X-Requested-With" in response.get_json()["message"]

    def test_the_upload_endpoint_is_refused(self, csrf_client, make_product):
        """The one that was actually reachable: multipart/form-data needs no
        preflight, so a plain <form> on another site could post to it."""
        product = make_product("Tigela")

        response = csrf_client.post(
            f"/api/products/{product['id']}/images/upload",
            data={"file": (BytesIO(b"not-a-real-image"), "x.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 403

    def test_the_collection_cover_is_refused(self, csrf_client, make_collection):
        collection = make_collection("Inverno")

        response = csrf_client.post(
            f"/api/collections/{collection['id']}/cover",
            data={"file": (BytesIO(b"not-a-real-image"), "x.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 403

    @pytest.mark.parametrize("method", ["put", "delete"])
    def test_every_unsafe_method_is_covered(self, csrf_client, method):
        """Not only POST. The API routes no PATCH anywhere, so these two are the
        rest of what a forged request could reach."""
        response = getattr(csrf_client, method)("/api/materials/1", json={"name": "x"})

        assert response.status_code == 403

    def test_reads_still_work(self, csrf_client):
        """A cross-site GET cannot be read back, so refusing one would cost the
        dashboard something and protect nothing."""
        assert csrf_client.get("/api/auth/me").status_code == 200

    def test_a_bearer_token_needs_no_header(self, anon_client, bearer):
        """An API client is not a browser and has no cookie to be used against
        it. curl and Swagger must not have to know about this."""
        response = anon_client.post(
            "/api/materials/", json={"name": "Cortiça"}, headers=bearer
        )

        assert response.status_code == 201

    def test_swagger_still_writes_from_a_browser_holding_a_session(
        self, csrf_client, bearer
    ):
        """The Authorize button sends a token but the browser sends the cookie
        too, and Swagger's own fetch() sets no header of ours. A valid token has
        to be enough on its own."""
        response = csrf_client.post(
            "/api/materials/", json={"name": "Bronze"}, headers=bearer
        )

        assert response.status_code == 201

    def test_contacts_put_is_guarded(self, anon_client):
        assert anon_client.put(
            "/api/contacts/", json={"email": "x@y.z"}
        ).status_code == 401

    def test_catalog_reads_stay_public(self, anon_client):
        """Guarding the writes must not lock the storefront out."""
        assert anon_client.get("/api/products/").status_code == 200
        assert anon_client.get("/api/materials/").status_code == 200
        assert anon_client.get("/api/collections/").status_code == 200


class TestSigningOut:
    def test_logout_empties_the_session(self, client):
        assert client.post("/api/auth/logout").status_code == 200

        with client.session_transaction() as flask_session:
            assert "user" not in flask_session

    def test_writes_are_refused_after_logout(self, client):
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").status_code == 401

    def test_logout_when_signed_out_is_not_an_error(self, anon_client):
        response = anon_client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.get_json()["message"] == "No user logged in"


class TestMe:
    def test_returns_the_signed_in_account(self, auth_client):
        assert auth_client.get("/api/auth/me").get_json()["username"] == "tokenuser"

    def test_never_returns_the_password(self, auth_client):
        assert "password" not in auth_client.get("/api/auth/me").get_json()

    def test_a_stale_session_is_rejected(self, client):
        """A signed cookie can outlive the row it points at."""
        with client.session_transaction() as flask_session:
            flask_session["user"] = {"id": 999999, "username": "ghost"}

        assert client.get("/api/auth/me").status_code == 401


class TestDocumentedStatusCodes:
    def test_guarded_endpoint_documents_its_401(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert "401" in schema["paths"]["/users/"]["get"]["responses"]

    def test_public_endpoint_documents_no_401(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert "401" not in schema["paths"]["/products/"]["get"]["responses"]


class TestDashboardPagesAreGuarded:
    """The guard is a blueprint-wide before_request rather than a decorator per
    view, so these walk the routes the app actually has: a page added without a
    guard fails here instead of shipping public."""

    @staticmethod
    def _dashboard_paths(app):
        return sorted(
            rule.rule
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith("web.dashboard.")
            and "GET" in (rule.methods or set())
        )

    def test_there_are_pages_to_guard(self, app):
        assert len(self._dashboard_paths(app)) >= 5

    def test_every_page_sends_an_anonymous_visitor_to_the_login(self, app, anon_client):
        for path in self._dashboard_paths(app):
            response = anon_client.get(path)
            assert response.status_code == 302, path
            assert "/auth" in response.headers["Location"], path

    def test_a_signed_in_visitor_gets_the_page(self, app, client):
        for path in self._dashboard_paths(app):
            response = client.get(path)
            # /dashboard itself redirects to /dashboard/home, which is not the
            # login page — that is the one legitimate redirect here.
            assert response.status_code in (200, 302), path
            if response.status_code == 302:
                assert "/auth" not in response.headers["Location"], path
