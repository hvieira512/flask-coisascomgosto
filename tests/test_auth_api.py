"""HTTP-level tests for /api/auth."""

import pytest


class TestRegister:
    def test_creates_and_returns_the_user(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "pw"},
        )
        assert response.status_code == 201

        body = response.get_json()
        assert body["username"] == "alice"
        assert body["email"] == "alice@example.com"

    def test_password_is_never_returned(self, client, make_user):
        assert "password" not in make_user("alice")

    def test_registration_ignores_anything_it_did_not_ask_for(self, client):
        """A payload field the model does not declare must not reach the insert.

        This was the is_admin regression: the flag was read straight from the
        request body, so anyone could register themselves an administrator. There
        are no roles at all now, and the guarantee that matters outlives the flag —
        an account is created from username, e-mail and password, and nothing else
        a caller sends.
        """
        response = client.post(
            "/api/auth/register",
            json={
                "username": "eve",
                "email": "eve@example.com",
                "password": "pw",
                "is_admin": True,
                "id": 999,
            },
        )
        assert response.status_code == 201

        body = response.get_json()
        assert set(body) == {"id", "username", "email", "created_at"}
        assert body["id"] != 999

    def test_duplicate_username_returns_409(self, client, make_user):
        make_user("alice", email="alice@example.com")

        response = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "other@example.com", "password": "pw"},
        )
        assert response.status_code == 409

    def test_duplicate_email_returns_409(self, client, make_user):
        make_user("alice", email="alice@example.com")

        response = client.post(
            "/api/auth/register",
            json={"username": "bob", "email": "alice@example.com", "password": "pw"},
        )
        assert response.status_code == 409

    @pytest.mark.parametrize("email", ["not-an-email", "no@tld", "@example.com"])
    def test_invalid_email_returns_400(self, client, email):
        response = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": email, "password": "pw"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "a@example.com", "password": "pw"},
            {"username": "alice", "password": "pw"},
            {"username": "alice", "email": "a@example.com"},
        ],
    )
    def test_missing_fields_return_400(self, client, payload):
        assert client.post("/api/auth/register", json=payload).status_code == 400


class TestLogin:
    def test_valid_credentials_return_the_user(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        )
        assert response.status_code == 200
        assert response.get_json()["user"]["username"] == "alice"

    def test_password_is_never_returned(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        body = client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        ).get_json()
        assert "password" not in body
        assert "password" not in body["user"]

    def test_wrong_password_returns_401(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        response = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
        assert response.status_code == 401

    def test_unknown_username_returns_404(self, client):
        response = client.post(
            "/api/auth/login", json={"username": "nobody", "password": "pw"}
        )
        assert response.status_code == 404

    def test_missing_fields_return_400(self, client):
        assert client.post("/api/auth/login", json={"username": "alice"}).status_code == 400

    def test_login_populates_the_session(self, client, make_user):
        make_user("alice", password="Passw0rd!")
        client.post("/api/auth/login", json={"username": "alice", "password": "Passw0rd!"})

        with client.session_transaction() as session:
            assert session["user"]["username"] == "alice"


class TestLogout:
    def test_clears_the_session(self, client, make_user):
        make_user("alice", password="Passw0rd!")
        client.post("/api/auth/login", json={"username": "alice", "password": "Passw0rd!"})

        response = client.post("/api/auth/logout")
        assert response.status_code == 200

        with client.session_transaction() as session:
            assert "user" not in session

    def test_logout_without_a_session_is_not_an_error(self, anon_client):
        """Anonymous: obtaining a token also establishes a server session."""
        response = anon_client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.get_json()["message"] == "No user logged in"
