"""Data access for the users table."""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

# Never selected alongside the public columns, so a password hash cannot
# leak into a marshalled response by accident.
_PUBLIC_COLUMNS = "id, username, email, created_at, is_admin"


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
        return self._cursor.fetchone()["total"]

    def get(self, user_id: int) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE id = %s", (user_id,)
        )
        return self._to_dict(self._cursor.fetchone())

    def get_by_username(self, username: str) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE username = %s", (username,)
        )
        return self._to_dict(self._cursor.fetchone())

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

    def create(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        is_admin: bool = False,
    ) -> int:
        """Insert a user and return the new ID. Expects an already-hashed password."""
        self._cursor.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
            (username, email, password_hash, bool(is_admin)),
        )
        return self._cursor.lastrowid

    @staticmethod
    def _to_dict(row) -> Optional[dict]:
        """Convert a driver row into a response-ready dict.

        created_at is serialised to ISO here rather than left to the marshalling
        layer, so the repository has one output shape whoever consumes it.
        """
        if not row:
            return None

        created_at = row["created_at"]

        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "created_at": created_at.isoformat() if created_at else None,
            # MySQL stores the flag as TINYINT(1), so 0/1 comes back, not a bool.
            "is_admin": bool(row["is_admin"]),
        }
