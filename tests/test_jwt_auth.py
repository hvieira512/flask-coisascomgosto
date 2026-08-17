"""Tests for the API's bearer-token authentication: issuing, guarding, refreshing.

The session path is covered in test_session_auth.py. A protected endpoint accepts
either, so these tests always send the header from an otherwise anonymous client
— never from `client`, which already holds a session and would pass regardless.
"""

from datetime import timedelta

import pytest

GUARDED = [
    ("get", "/api/users/"),
    ("get", "/api/users/1"),
    ("get", "/api/contacts/"),
    ("get", "/api/auth/me"),
]


class TestTokenIssuing:
    def test_login_returns_an_access_and_refresh_token(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        body = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()

        assert body["access_token"]
        assert body["refresh_token"]
        assert body["access_token"] != body["refresh_token"]

    def test_login_also_returns_the_user(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        body = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()
        assert body["user"]["username"] == "alice"
        assert "password" not in body["user"]

    def test_bad_password_issues_no_token(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        response = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
        assert response.status_code == 401
        assert "access_token" not in response.get_json()

    def test_token_carries_the_username_claim(self, app, tokens):
        """is_admin rides along so a guard needs no database round trip."""
        from flask_jwt_extended import decode_token

        with app.app_context():
            claims = decode_token(tokens["access_token"])

        assert claims["username"] == "apiclient"
        assert claims["is_admin"] is False


class TestGuards:
    @pytest.mark.parametrize("method,path", GUARDED)
    def test_with_no_credential_returns_401(self, anon_client, method, path):
        assert getattr(anon_client, method)(path).status_code == 401

    @pytest.mark.parametrize("method,path", GUARDED)
    def test_a_bearer_token_is_accepted(self, anon_client, bearer, method, path):
        assert getattr(anon_client, method)(path, headers=bearer).status_code != 401

    def test_a_bearer_token_authorises_a_write(self, anon_client, bearer):
        response = anon_client.post(
            "/api/categories/", json={"name": "Cortiça"}, headers=bearer
        )
        assert response.status_code == 201

    def test_garbage_token_is_rejected(self, anon_client):
        response = anon_client.get(
            "/api/users/", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert response.status_code in (401, 422)

    def test_missing_bearer_prefix_is_rejected(self, anon_client, tokens):
        response = anon_client.get(
            "/api/users/", headers={"Authorization": tokens["access_token"]}
        )
        assert response.status_code in (401, 422)

    def test_catalog_reads_stay_public(self, anon_client):
        """Guarding the writes must not lock the storefront out."""
        assert anon_client.get("/api/products/").status_code == 200
        assert anon_client.get("/api/categories/").status_code == 200
        assert anon_client.get("/api/collections/").status_code == 200


class TestRefreshFlow:
    def test_refresh_token_mints_a_new_access_token(self, anon_client, tokens):
        response = anon_client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert response.status_code == 200
        assert response.get_json()["access_token"]

    def test_the_new_access_token_works(self, anon_client, tokens):
        fresh = anon_client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        ).get_json()["access_token"]

        response = anon_client.get(
            "/api/users/", headers={"Authorization": f"Bearer {fresh}"}
        )
        assert response.status_code == 200

    def test_an_access_token_cannot_be_used_to_refresh(self, anon_client, tokens):
        """Only a refresh token may hit /auth/refresh."""
        response = anon_client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code in (401, 422)

    def test_refresh_without_a_token_returns_401(self, anon_client):
        assert anon_client.post("/api/auth/refresh").status_code == 401

    def test_expired_access_token_is_rejected_then_refreshed(
        self, app, anon_client, make_user
    ):
        """The whole point of the refresh flow, end to end."""
        from flask_jwt_extended import create_access_token

        make_user("alice", password="Passw0rd!")
        pair = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()

        # An access token that expired a minute ago.
        with app.app_context():
            expired = create_access_token(
                identity="1", expires_delta=timedelta(seconds=-60)
            )

        # A fresh client, so the session the login above set does not mask the
        # rejection: the guard would otherwise accept the cookie.
        api = app.test_client()
        assert api.get(
            "/api/users/", headers={"Authorization": f"Bearer {expired}"}
        ).status_code == 401

        fresh = api.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {pair['refresh_token']}"},
        ).get_json()["access_token"]

        assert api.get(
            "/api/users/", headers={"Authorization": f"Bearer {fresh}"}
        ).status_code == 200


class TestMe:
    def test_returns_the_token_owner(self, anon_client, bearer):
        body = anon_client.get("/api/auth/me", headers=bearer).get_json()
        assert body["username"] == "apiclient"

    def test_never_returns_the_password(self, anon_client, bearer):
        assert "password" not in anon_client.get("/api/auth/me", headers=bearer).get_json()


class TestSwaggerDocumentsAuth:
    def test_bearer_security_scheme_is_published(self, anon_client):
        """This is what renders the Authorize button in /api/docs."""
        schema = anon_client.get("/api/swagger.json").get_json()
        assert "Bearer" in schema["securityDefinitions"]
        assert schema["securityDefinitions"]["Bearer"]["in"] == "header"
        assert schema["securityDefinitions"]["Bearer"]["name"] == "Authorization"

    def test_guarded_endpoint_declares_security(self, anon_client):
        schema = anon_client.get("/api/swagger.json").get_json()
        assert schema["paths"]["/users/"]["get"].get("security")

    def test_every_write_declares_security(self, anon_client):
        """A padlock missing from one write is how an endpoint quietly stops
        looking protected in the docs."""
        schema = anon_client.get("/api/swagger.json").get_json()

        unprotected = [
            f"{verb.upper()} {path}"
            for path, methods in schema["paths"].items()
            for verb, spec in methods.items()
            if verb in {"post", "put", "delete"}
            and not spec.get("security")
            and not path.startswith("/auth/")
        ]
        assert unprotected == []

    def test_public_endpoint_declares_no_security(self, anon_client):
        schema = anon_client.get("/api/swagger.json").get_json()
        assert not schema["paths"]["/products/"]["get"].get("security")
