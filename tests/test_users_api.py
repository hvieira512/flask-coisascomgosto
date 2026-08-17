"""HTTP-level tests for /api/users.

Every endpoint is behind a bearer token, so these use the `auth_client`
fixture. The guard itself is covered in test_session_auth.py.
"""


class TestListUsers:
    def test_lists_only_the_token_owner_initially(self, auth_client):
        """The auth_client fixture registers one user to obtain its token."""
        body = auth_client.get("/api/users/").get_json()
        assert [u["username"] for u in body["users"]] == ["tokenuser"]
        assert body["pagination"]["total"] == 1

    def test_lists_registered_users(self, auth_client, make_user):
        make_user("alice")
        make_user("bob")

        body = auth_client.get("/api/users/").get_json()
        assert "alice" in [u["username"] for u in body["users"]]
        assert body["pagination"]["total"] == 3

    def test_password_is_never_listed(self, auth_client, make_user):
        make_user("alice")

        for user in auth_client.get("/api/users/").get_json()["users"]:
            assert "password" not in user

    def test_pagination_splits_results(self, auth_client, make_user):
        for name in ["alice", "bob", "carol"]:
            make_user(name)

        body = auth_client.get("/api/users/?page=2&limit=2").get_json()
        assert len(body["users"]) == 2
        assert body["pagination"]["page"] == 2

    def test_invalid_pagination_returns_400(self, auth_client):
        assert auth_client.get("/api/users/?limit=0").status_code == 400


class TestGetUser:
    def test_returns_existing_user(self, auth_client, make_user):
        created = make_user("alice")

        body = auth_client.get(f"/api/users/{created['id']}").get_json()
        assert body["username"] == "alice"

    def test_password_is_never_returned(self, auth_client, make_user):
        created = make_user("alice")

        assert "password" not in auth_client.get(
            f"/api/users/{created['id']}"
        ).get_json()

    def test_unknown_id_returns_404(self, auth_client):
        assert auth_client.get("/api/users/9999").status_code == 404
