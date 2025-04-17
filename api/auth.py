from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from api.users import (
    email_exists,
    get_user_by_id,
    get_user_by_username,
    username_exists,
)
from api.utils import execute, is_email_valid

bp = Blueprint("auth", __name__)

# ----------------
# Helper functions
# ----------------


def validate_register(data):
    expected = {
        "username": "coisascomgosto",
        "email": "coisascomgosto@hotmail.com",
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


def validate_login(data):
    expected = {"username": "coisascomgosto", "password": "i_love_coisascomgosto"}

    if "username" not in data or not isinstance(data.get("username"), str):
        return jsonify(
            {
                "error": "Field 'username' is required and must be a string.",
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


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    err = validate_login(data)
    if err:
        return err

    user = get_user_by_username(data["username"])

    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid login."}), 404

    session["id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = user["is_admin"]

    return jsonify({"message": "Login successful", "user": dict(session)})


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    error = validate_login(data)
    if error:
        return error

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if username_exists(username):
        return jsonify({"error": "This username is already taken."}), 409

    if email_exists(email):
        return jsonify({"error": "This email is already taken."}), 409

    if not is_email_valid(email):
        return jsonify({"error": "Invalid email."}), 400

    hashed_password = generate_password_hash(password)

    id = execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, hashed_password),
    )

    if not id:
        return jsonify({"error": "Failed to create user."}), 500

    user = get_user_by_id(id)

    return jsonify(
        {
            "message": "User created successfully",
            "user": user,
        }
    ), 201


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logout successful"}), 200
