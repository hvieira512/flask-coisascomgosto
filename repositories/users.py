"""Data access for the users table."""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

from repositories.base import one_row

_PUBLIC_COLUMNS = "id, username, email, created_at"


class UserRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(self, *, limit: int, offset: int) -> list[dict]:
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS} FROM users ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return [self._to_dict(row) for row in self._cursor.fetchall()]

    def count(self) -> int:
        self._cursor.execute("SELECT COUNT(*) AS total FROM users")
        return one_row(self._cursor)["total"]

    def get(self, user_id: int) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE id = %s", (user_id,)
        )
        row = self._cursor.fetchone()
        return self._to_dict(row) if row else None

    def get_by_username(self, username: str) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE username = %s", (username,)
        )
        row = self._cursor.fetchone()
        return self._to_dict(row) if row else None

    def get_credentials(self, username: str) -> Optional[dict]:
        """Return the stored password hash plus public fields, for login only."""
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS}, password FROM users WHERE username = %s",
            (username,),
        )
        row = self._cursor.fetchone()
        if not row:
            return None

        # Reuse the same normalization as every other read, so created_at is
        # serialised the same way here as everywhere else.
        user = self._to_dict(row)
        user["password"] = row["password"]
        return user

    def exists(self, user_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        return self._cursor.fetchone() is not None

    def username_exists(self, username: str) -> bool:
        self._cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        return self._cursor.fetchone() is not None

    def email_exists(self, email: str) -> bool:
        self._cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        return self._cursor.fetchone() is not None

    def create(self, *, username: str, email: str, password_hash: str) -> int:
        """Insert a user and return the new ID. Expects an already-hashed password."""
        self._cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password_hash),
        )
        return self._cursor.lastrowid

    @staticmethod
    def _to_dict(row) -> dict:
        """Convert a driver row into a response-ready dict.

        created_at is serialised to ISO here rather than left to the marshalling
        layer, so the repository has one output shape whoever consumes it.

        It used to take an absent row and answer None, which made every caller's
        result optional whether it could be absent or not: `list()` came out as
        list[dict | None] though fetchall() yields only rows, and
        `get_credentials` had to subscript a value the checker knew might be None.
        Deciding "was there a row" is the caller's business, and each of them
        already knows.
        """
        created_at = row["created_at"]

        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "created_at": created_at.isoformat() if created_at else None,
        }
