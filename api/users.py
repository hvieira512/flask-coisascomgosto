from flask import Blueprint, jsonify, request

from api.utils import execute, fetch_all, fetch_one, format_datetime


bp = Blueprint("user", __name__)


# ----------------
# Helper functions
# ----------------


def get_user_by_id(id: int):
    user = fetch_one(
        "SELECT id, username, email, created_at, is_admin FROM users WHERE id=?",
        (id,),
    )
    if user:
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": format_datetime(user["created_at"]),
            "is_admin": bool(user["is_admin"]),
        }
    return None


def get_user_by_username(username: str):
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username,))
    if user:
        return dict(user)
    return None


def username_exists(username: str) -> bool:
    query = "SELECT * FROM users WHERE username=?"
    return fetch_one(query, (username,)) is not None


def email_exists(email: str) -> bool:
    query = "SELECT * FROM users WHERE email=?"
    return fetch_one(query, (email,)) is not None


def validate_json(data):
    expected = {
        "username": "huvieira",
        "email": "huvieira@email.com",
        "password": "i_love_coisascomgosto",
    }

    if "username" not in data or not isinstance(data.get("username"), str):
        return jsonify(
            {
                "error": "Field 'name' is required and must be a string.",
                "expected": expected,
            }
        ), 400

    if "email" not in data or not isinstance(data.get("email"), str):
        return jsonify(
            {
                "error": "Field 'email' is required and must be a string.",
                "expected": expected,
            }
        ), 400

    if "password" not in data or not isinstance(data.get("password"), str):
        return jsonify(
            {
                "error": "Field 'password' is required and must be a string.",
                "expected": expected,
            }
        ), 400

    return None


# ----------------
# Route handlers
# ----------------


@bp.route("")
def get_users():
    rows = fetch_all("SELECT id, username, email, created_at, is_admin FROM users")

    users = []
    for user in rows:
        users.append(
            {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "created_at": format_datetime(user["created_at"]),
                "is_admin": bool(user["is_admin"]),
            }
        )

    return jsonify(users)


@bp.route("/<int:id>")
def get_user(id):
    user = get_user_by_id(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user)


@bp.route("/<int:id>", methods=["PUT"])
def update_user(id):
    user = get_user_by_id(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    username = data.get("username", user["username"])
    email = data.get("email", user["email"])
    is_admin = data.get("is_admin", user["is_admin"])

    if username_exists(username) and username != user["username"]:
        return jsonify({"error": "This username is already taken."}), 409

    if email_exists(email) and email != user["email"]:
        return jsonify({"error": "This email is already taken."}), 409

    execute(
        "UPDATE users SET username=?, email=?, is_admin=? WHERE id=?",
        (username, email, is_admin, id),
    )

    updated_user = get_user_by_id(id)
    return jsonify(
        {
            "message": "User updated successfully",
            "user": updated_user,
        }
    )


@bp.route("/<int:id>", methods=["DELETE"])
def delete_user(id):
    user = get_user_by_id(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    execute("DELETE FROM users WHERE id=?", (id,))

    return jsonify(
        {
            "message": "User deleted successfully",
            "user": user,
        }
    )
