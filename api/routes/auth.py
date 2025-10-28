from flask import session
from flask_restx import Namespace, Resource
from werkzeug.security import check_password_hash, generate_password_hash

from api.helpers.users import (
    email_exists,
    fetch_user_by_id,
    username_exists,
)
from api.models.auth import login_model, register_model
from api.models.users import user_model
from api.utils import get_db_connection, is_email_valid

ns = Namespace("auth", description="Authentication operations")

ns.models[login_model.name] = login_model
ns.models[register_model.name] = register_model
ns.models[user_model.name] = user_model


@ns.route("/register")
class Register(Resource):
    @ns.expect(register_model, validate=True)
    @ns.marshal_with(user_model)
    def post(self):
        """Register"""
        data = ns.payload

        username = data["username"]
        email = data["email"]
        password = data["password"]
        is_admin = data.get("is_admin", False)

        if not is_email_valid(email):
            ns.abort(400, "This email is not valid")

        with get_db_connection() as (conn, cursor):
            if username_exists(cursor, username):
                ns.abort(409, "This username is already taken")

            if email_exists(cursor, email):
                ns.abort(409, "This email is already taken")

            hashed_password = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, is_admin),
            )
            user_id = cursor.lastrowid
            user = fetch_user_by_id(cursor, user_id)

            conn.commit()
            return user, 201


@ns.route("/login")
class Login(Resource):
    @ns.expect(login_model, validate=True)
    @ns.marshal_with(user_model)
    def post(self):
        """Login"""
        if "user" in session:
            return session["user"], 200

        data = ns.payload

        username = data["username"]
        password = data["password"]

        with get_db_connection() as (_, cursor):
            cursor.execute(
                "SELECT id, username, email, is_admin, password FROM users WHERE username = ?",
                (username,),
            )
            user = cursor.fetchone()
            if not user:
                ns.abort(404, "User invalid.")

            if not check_password_hash(user["password"], password):
                ns.abort(401, "Invalid login.")

            user_safe = {k: v for k, v in dict(user).items() if k != "password"}
            session["user"] = user_safe

            return user_safe, 200


@ns.route("/logout")
class Logout(Resource):
    def post(self):
        """Logout the current user"""
        user = session.pop("user", None)
        msg = "Successfully logged out" if user else "No user logged in"
        return {"message": msg}, 200
