"""Tests for the session half of authentication.

The dashboard's pages are rendered server-side, so they cannot carry a token from
localStorage — they are gated by Flask's session cookie instead, and the API
guard accepts it alongside a bearer token. The token half is covered in
test_jwt_auth.py.
"""

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
