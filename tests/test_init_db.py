"""init_db drops and recreates every table, which is how a schema change is
applied. On 2026-08-18 that silently emptied the users table on a real database
and left the owners locked out of their own dashboard with nothing to log in
with — schema.sql seeds the catalog's lookups but, rightly, no accounts.

These pin the two halves of the fix: the accounts survive a rebuild, and the
suite still gets the blank slate it needs.
"""

from api.db import get_db_connection, init_db
from api.repositories import UserRepository


# Each helper opens and closes its own connection. init_db drops tables, and
# MySQL makes DDL wait on the metadata locks an open transaction holds — sharing
# the suite's long-lived `cursor` fixture here hangs the run instead of failing
# it, which is a nasty way to find out.
def _create_user(**kwargs):
    with get_db_connection() as (_, cursor):
        return UserRepository(cursor).create(**kwargs)


def _usernames():
    with get_db_connection() as (_, cursor):
        cursor.execute("SELECT username FROM users ORDER BY id")
        return [row["username"] for row in cursor.fetchall()]


def _one(sql, params=()):
    with get_db_connection() as (_, cursor):
        cursor.execute(sql, params)
        return cursor.fetchone()


class TestInitDbKeepsAccounts:
    def test_accounts_survive_a_schema_rebuild(self):
        _create_user(
            username="hugo", email="hugo@example.com", password_hash="hashed"
        )

        init_db()

        assert _usernames() == ["hugo"]

    def test_the_password_hash_survives_too(self):
        """A preserved row that cannot be logged into is no better than none."""
        _create_user(
            username="hugo", email="hugo@example.com", password_hash="hashed"
        )

        init_db()

        assert _one(
            "SELECT password FROM users WHERE username = %s", ("hugo",)
        )["password"] == "hashed"

    def test_ids_are_kept_so_references_still_point_at_the_same_person(self):
        first = _create_user(
            username="hugo", email="hugo@example.com", password_hash="h"
        )
        second = _create_user(
            username="maria", email="maria@example.com", password_hash="h"
        )

        init_db()

        with get_db_connection() as (_, cursor):
            cursor.execute("SELECT id, username FROM users ORDER BY id")
            assert [(r["id"], r["username"]) for r in cursor.fetchall()] == [
                (first, "hugo"),
                (second, "maria"),
            ]

    def test_admin_stays_admin(self):
        _create_user(
            username="hugo",
            email="hugo@example.com",
            password_hash="h",
            is_admin=True,
        )

        init_db()

        assert _one("SELECT is_admin FROM users WHERE username = 'hugo'")["is_admin"] == 1

    def test_the_catalog_is_still_rebuilt(self):
        """Preserving accounts must not turn init-db into a no-op: everything
        else is still meant to go."""
        with get_db_connection() as (_, cursor):
            cursor.execute(
                "INSERT INTO product_types (name) VALUES (%s)", ("Caixa",)
            )
        _create_user(username="hugo", email="hugo@example.com", password_hash="h")

        init_db()

        assert _one("SELECT COUNT(*) AS n FROM product_types")["n"] == 0

    def test_keep_users_false_empties_the_table(self):
        """What the suite asks for, and the only way to get a blank slate."""
        _create_user(username="hugo", email="hugo@example.com", password_hash="h")

        init_db(keep_users=False)

        assert _usernames() == []

    def test_an_empty_users_table_is_not_a_problem(self):
        init_db()
        assert _usernames() == []
