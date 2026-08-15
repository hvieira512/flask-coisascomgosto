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

    def test_new_users_are_not_admins(self, client, make_user):
        assert make_user("alice")["is_admin"] is False

    def test_is_admin_cannot_be_set_from_the_payload(self, client):
        """Regression: is_admin was read straight from the request body."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "eve",
                "email": "eve@example.com",
                "password": "pw",
                "is_admin": True,
            },
        )
        assert response.status_code == 201
        assert response.get_json()["is_admin"] is False

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

    def test_wrong_password_returns_401(self, client, make_user):
        make_user("alice", password="Passw0rd!")

        response = client.post(
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

    def test_logout_without_a_session_is_not_an_error(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.get_json()["message"] == "No user logged in"
