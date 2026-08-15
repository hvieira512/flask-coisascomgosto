"""Tests for JWT bearer authentication: issuing, guarding and refreshing."""

from datetime import timedelta

import pytest

GUARDED = [
    ("get", "/api/users/"),
    ("get", "/api/users/1"),
    ("get", "/api/contacts/"),
    ("get", "/api/auth/me"),
]


class TestTokenIssuing:
    def test_login_returns_an_access_and_refresh_token(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        body = client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()

        assert body["access_token"]
        assert body["refresh_token"]
        assert body["access_token"] != body["refresh_token"]

    def test_login_still_returns_the_user(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        body = client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()
        assert body["user"]["username"] == "alice"

    def test_bad_password_issues_no_token(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
        assert response.status_code == 401
        assert "access_token" not in response.get_json()

    def test_token_carries_the_username_claim(self, app, tokens):
        from flask_jwt_extended import decode_token

        with app.app_context():
            claims = decode_token(tokens["access_token"])

        assert claims["username"] == "tokenuser"
        assert claims["is_admin"] is False


class TestGuards:
    @pytest.mark.parametrize("method,path", GUARDED)
    def test_without_a_token_returns_401(self, client, method, path):
        assert getattr(client, method)(path).status_code == 401

    @pytest.mark.parametrize("method,path", GUARDED)
    def test_with_a_token_is_allowed(self, auth_client, method, path):
        assert getattr(auth_client, method)(path).status_code != 401

    def test_garbage_token_returns_422(self, client):
        response = client.get(
            "/api/users/", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert response.status_code in (401, 422)

    def test_missing_bearer_prefix_returns_401(self, client, tokens):
        response = client.get(
            "/api/users/", headers={"Authorization": tokens["access_token"]}
        )
        assert response.status_code in (401, 422)

    def test_contacts_put_is_guarded(self, client):
        assert client.put("/api/contacts/", json={"email": "x@y.z"}).status_code == 401

    def test_catalog_reads_stay_public(self, client):
        """Guarding users and contacts must not lock the storefront out."""
        assert client.get("/api/products/").status_code == 200
        assert client.get("/api/categories/").status_code == 200
        assert client.get("/api/collections/").status_code == 200


class TestRefreshFlow:
    def test_refresh_token_mints_a_new_access_token(self, client, tokens):
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert response.status_code == 200
        assert response.get_json()["access_token"]

    def test_the_new_access_token_works(self, client, tokens):
        fresh = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        ).get_json()["access_token"]

        response = client.get(
            "/api/users/", headers={"Authorization": f"Bearer {fresh}"}
        )
        assert response.status_code == 200

    def test_an_access_token_cannot_be_used_to_refresh(self, client, tokens):
        """Only a refresh token may hit /auth/refresh."""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code in (401, 422)

    def test_refresh_without_a_token_returns_401(self, client):
        assert client.post("/api/auth/refresh").status_code == 401

    def test_expired_access_token_is_rejected_then_refreshed(
        self, app, client, make_user
    ):
        """The whole point of the refresh flow, end to end."""
        from flask_jwt_extended import create_access_token

        make_user("alice", password="Passw0rd!")
        tokens = client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()

        # An access token that expired a minute ago.
        with app.app_context():
            expired = create_access_token(
                identity="1", expires_delta=timedelta(seconds=-60)
            )

        assert (
            client.get(
                "/api/users/", headers={"Authorization": f"Bearer {expired}"}
            ).status_code
            == 401
        )

        # The refresh token is still good, so the client recovers without
        # asking for the password again.
        fresh = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        ).get_json()["access_token"]

        assert (
            client.get(
                "/api/users/", headers={"Authorization": f"Bearer {fresh}"}
            ).status_code
            == 200
        )


class TestMe:
    def test_returns_the_token_owner(self, auth_client):
        assert auth_client.get("/api/auth/me").get_json()["username"] == "tokenuser"

    def test_never_returns_the_password(self, auth_client):
        assert "password" not in auth_client.get("/api/auth/me").get_json()


class TestSwaggerDocumentsAuth:
    def test_bearer_security_scheme_is_published(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert "Bearer" in schema["securityDefinitions"]

    def test_guarded_endpoint_declares_security(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert schema["paths"]["/users/"]["get"].get("security")

    def test_public_endpoint_declares_no_security(self, client):
        schema = client.get("/api/swagger.json").get_json()
        assert not schema["paths"]["/products/"]["get"].get("security")
