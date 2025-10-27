from datetime import datetime
from sqlite3 import Cursor
from typing import Optional


def fetch_user_by_id(cursor: Cursor, user_id: int) -> Optional[dict]:
    """Return a user dict by ID, or None if not found."""
    cursor.execute(
        "SELECT id, username, email, created_at, is_admin FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    return _format_user_row(row)


def fetch_user_by_username(cursor: Cursor, username: str) -> Optional[dict]:
    """Return a user dict by username, or None if not found."""
    cursor.execute(
        "SELECT id, username, email, created_at, is_admin FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    return _format_user_row(row)


def username_exists(cursor: Cursor, username: str) -> bool:
    """Check if a username already exists."""
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    return cursor.fetchone() is not None


def email_exists(cursor: Cursor, email: str) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    return cursor.fetchone() is not None


def user_exists_by_id(cursor: Cursor, user_id: int) -> bool:
    """Check if a user exists by ID."""
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None


def _format_user_row(r) -> Optional[dict]:
    """Convert a sqlite3.Row into a properly formatted dict."""
    if not r:
        return None

    created_at = r["created_at"]
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            pass

    return {
        "id": r["id"],
        "username": r["username"],
        "email": r["email"],
        "created_at": created_at.isoformat()
        if isinstance(created_at, datetime)
        else created_at,
        "is_admin": bool(r["is_admin"]),
    }
