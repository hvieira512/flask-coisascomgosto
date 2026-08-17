"""Tests for session authentication: signing in, guarding, signing out."""

import pytest

GUARDED = [
    ("get", "/api/users/"),
    ("get", "/api/users/1"),
    ("get", "/api/contacts/"),
    ("get", "/api/auth/me"),
]


class TestSigningIn:
    def test_login_returns_the_user(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        body = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()

        assert body["username"] == "alice"
        assert body["is_admin"] is False

    def test_login_never_returns_the_password(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        body = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()
        assert "password" not in body

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
        """One sign-in is enough; there is no token to attach per call."""
        assert client.get("/api/auth/me").status_code == 200
        assert client.get("/api/auth/me").status_code == 200


class TestGuards:
    @pytest.mark.parametrize("method,path", GUARDED)
    def test_signed_out_returns_401(self, anon_client, method, path):
        assert getattr(anon_client, method)(path).status_code == 401

    @pytest.mark.parametrize("method,path", GUARDED)
    def test_signed_in_is_allowed(self, auth_client, method, path):
        assert getattr(auth_client, method)(path).status_code != 401

    def test_a_stale_bearer_header_buys_nothing(self, anon_client):
        """Tokens are gone: an Authorization header is now just noise."""
        response = anon_client.get(
            "/api/users/", headers={"Authorization": "Bearer whatever"}
        )
        assert response.status_code == 401

    def test_contacts_put_is_guarded(self, anon_client):
        assert anon_client.put(
            "/api/contacts/", json={"email": "x@y.z"}
        ).status_code == 401

    def test_catalog_reads_stay_public(self, anon_client):
        """Guarding the writes must not lock the storefront out."""
        assert anon_client.get("/api/products/").status_code == 200
        assert anon_client.get("/api/categories/").status_code == 200
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


class TestSwaggerDocumentsAuth:
    def test_no_bearer_scheme_is_published(self, client):
        """The API stopped speaking bearer tokens, so it must stop advertising
        an Authorize button that cannot work."""
        schema = client.get("/api/swagger.json").get_json()
        assert "securityDefinitions" not in schema

    def test_guarded_endpoint_documents_its_401(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert "401" in schema["paths"]["/users/"]["get"]["responses"]

    def test_public_endpoint_documents_no_401(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert "401" not in schema["paths"]["/products/"]["get"]["responses"]
