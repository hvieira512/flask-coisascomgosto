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

    def test_a_missing_username_is_still_a_400(self, client):
        assert client.post("/api/auth/login", json={"password": "pw"}).status_code == 400

    def test_login_populates_the_session(self, client, make_user):
        make_user("alice", password="Passw0rd!")
        client.post("/api/auth/login", json={"username": "alice", "password": "Passw0rd!"})

        with client.session_transaction() as session:
            assert session["user"]["username"] == "alice"


class TestAskingWhetherAnAccountExists:
    """The login page asks for the username first and the password on a second
    screen, and picks which screen from the status code. Sending only a username
    is that question — it used to be asked by sending the password "fake", which
    made every visit to /auth a failed login."""

    def test_a_known_username_answers_401(self, anon_client, make_user):
        make_user("alice", password="Passw0rd!")

        response = anon_client.post("/api/auth/login", json={"username": "alice"})

        assert response.status_code == 401

    def test_an_unknown_username_answers_404(self, anon_client):
        response = anon_client.post("/api/auth/login", json={"username": "nobody"})

        assert response.status_code == 404

    def test_it_never_reaches_the_stored_hash(self, anon_client, make_user, monkeypatch):
        """Not only wasted work — scrypt on every page load is a way to make the
        server do something expensive for free."""
        import api.routes.auth as auth

        def fail(*args, **kwargs):
            raise AssertionError("the password hash was checked")

        make_user("alice", password="Passw0rd!")
        monkeypatch.setattr(auth, "check_password_hash", fail)

        assert anon_client.post(
            "/api/auth/login", json={"username": "alice"}
        ).status_code == 401

    def test_it_is_not_counted_as_a_failed_attempt(self, anon_client, make_user):
        """Otherwise opening the login page six times would lock the owners out of
        their own dashboard."""
        from api.rate_limit import FAILURES_ALLOWED

        make_user("alice", password="Passw0rd!")
        for _ in range(FAILURES_ALLOWED + 2):
            anon_client.post("/api/auth/login", json={"username": "alice"})

        response = anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "Passw0rd!"}
        )

        assert response.status_code == 200


class TestGuessingIsCounted:
    """/auth/login is otherwise an unmetered password oracle: nothing anywhere
    counts how many times a guess has been wrong."""

    @staticmethod
    def _guess(client, password="wrong"):
        return client.post(
            "/api/auth/login", json={"username": "alice", "password": password}
        )

    @pytest.fixture()
    def alice(self, make_user):
        return make_user("alice", password="Passw0rd!")

    def test_the_attempt_after_the_allowance_is_refused(self, anon_client, alice):
        from api.rate_limit import FAILURES_ALLOWED

        for attempt in range(FAILURES_ALLOWED):
            assert self._guess(anon_client).status_code == 401, attempt

        refused = self._guess(anon_client)

        assert refused.status_code == 429
        assert "failed attempts" in refused.get_json()["message"]

    def test_the_right_password_still_works_before_the_limit(self, anon_client, alice):
        from api.rate_limit import FAILURES_ALLOWED

        for _ in range(FAILURES_ALLOWED - 1):
            self._guess(anon_client)

        assert self._guess(anon_client, "Passw0rd!").status_code == 200

    def test_the_lockout_holds_even_with_the_right_password(self, anon_client, alice):
        """The point of a lockout is that the next guess is not tried, and the
        attacker's next guess could be the right one."""
        from api.rate_limit import FAILURES_ALLOWED

        for _ in range(FAILURES_ALLOWED):
            self._guess(anon_client)

        assert self._guess(anon_client, "Passw0rd!").status_code == 429

    def test_signing_in_clears_the_record(self, anon_client, alice):
        """Four typos and then success should not leave the account one attempt
        from a lockout."""
        from api.rate_limit import FAILURES_ALLOWED

        for _ in range(FAILURES_ALLOWED - 1):
            self._guess(anon_client)
        self._guess(anon_client, "Passw0rd!")

        for attempt in range(FAILURES_ALLOWED):
            assert self._guess(anon_client).status_code == 401, attempt

    def test_the_count_is_per_username(self, anon_client, alice, make_user):
        """One account under attack must not lock the other owner out."""
        from api.rate_limit import FAILURES_ALLOWED

        make_user("bob", password="Passw0rd!")
        for _ in range(FAILURES_ALLOWED + 1):
            self._guess(anon_client)

        assert anon_client.post(
            "/api/auth/login", json={"username": "bob", "password": "Passw0rd!"}
        ).status_code == 200

    def test_failures_age_out_of_the_window(self, anon_client, alice, monkeypatch):
        """The window is what releases the account; there is no expiry stored and
        nothing to sweep."""
        from api import rate_limit

        for _ in range(rate_limit.FAILURES_ALLOWED):
            self._guess(anon_client)
        assert self._guess(anon_client).status_code == 429

        monkeypatch.setattr(rate_limit.logins, "window_seconds", 0)

        assert self._guess(anon_client, "Passw0rd!").status_code == 200

    def test_a_refusal_does_not_extend_the_lockout(self, anon_client, alice):
        """Counting refusals would mean someone who keeps knocking keeps the
        owners locked out for as long as they care to."""
        from api import rate_limit

        for _ in range(rate_limit.FAILURES_ALLOWED):
            self._guess(anon_client)
        for _ in range(5):
            self._guess(anon_client)

        assert len(rate_limit.logins._hits["alice"]) == rate_limit.FAILURES_ALLOWED

    def test_an_unknown_username_is_counted_too(self, anon_client):
        """Working through a list of guessed usernames is the other way to use
        this endpoint, and it costs nothing if only real accounts are counted."""
        from api import rate_limit

        for _ in range(rate_limit.FAILURES_ALLOWED):
            assert anon_client.post(
                "/api/auth/login", json={"username": "ghost", "password": "x"}
            ).status_code == 404

        assert anon_client.post(
            "/api/auth/login", json={"username": "ghost", "password": "x"}
        ).status_code == 429


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
