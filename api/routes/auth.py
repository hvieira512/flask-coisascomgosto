"""Authentication.

    POST /auth/register -> a new account
    POST /auth/login    -> the account, and a session cookie
    GET  /auth/me       -> the caller's own user record
    POST /auth/logout   -> clears the session

Logging in sets Flask's session cookie, which the browser then sends on every
request — page loads and fetch() alike. That is the whole mechanism: there is no
token to store, refresh or attach.
"""

import re

from flask import session
from flask_restx import Namespace, Resource
from werkzeug.security import check_password_hash, generate_password_hash

from api.db import get_db_connection
from api.models.auth import login_model, register_model
from api.models.users import user_model
from api.repositories import UserRepository
from api.security import PROTECTED_DOC, login_required

ns = Namespace("auth", description="Authentication operations")

# Deliberately loose: this rejects typos, not exotic-but-valid addresses. The
# only real proof an address works is sending to it.
EMAIL = re.compile(r"([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Za-z]{2,})+")

for model in [login_model, register_model, user_model]:
    ns.models[model.name] = model


@ns.route("/register")
class Register(Resource):
    @ns.expect(register_model, validate=True)
    @ns.marshal_with(user_model)
    @ns.response(201, "Account created")
    @ns.response(400, "Invalid e-mail or missing fields")
    @ns.response(409, "Username or e-mail already taken")
    def post(self):
        """Register a new account."""
        data = ns.payload

        username = data["username"]
        email = data["email"]
        password = data["password"]

        if not EMAIL.fullmatch(email):
            ns.abort(400, "This email is not valid")

        with get_db_connection() as (_, cursor):
            users = UserRepository(cursor)

            if users.username_exists(username):
                ns.abort(409, "This username is already taken")

            if users.email_exists(email):
                ns.abort(409, "This email is already taken")

            # is_admin is deliberately not taken from the payload: it would let
            # anyone self-register as an administrator.
            user_id = users.create(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False,
            )
            return users.get(user_id), 201


@ns.route("/login")
class Login(Resource):
    @ns.expect(login_model, validate=True)
    @ns.marshal_with(user_model)
    @ns.response(200, "The authenticated account")
    @ns.response(401, "Invalid password")
    @ns.response(404, "Unknown username")
    def post(self):
        """Sign in, and receive the session cookie."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            credentials = UserRepository(cursor).get_credentials(data["username"])
            if not credentials:
                ns.abort(404, "User invalid.")

            if not check_password_hash(credentials["password"], data["password"]):
                ns.abort(401, "Invalid login.")

            user = {k: v for k, v in credentials.items() if k != "password"}
            session["user"] = user
            return user, 200


@ns.route("/me")
class Me(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(user_model)
    @ns.response(200, "The authenticated user")
    @login_required
    def get(self):
        """Return the signed-in account."""
        with get_db_connection() as (_, cursor):
            user = UserRepository(cursor).get(session["user"]["id"])
            if not user:
                session.clear()
                ns.abort(401, "This account no longer exists.")

            return user


@ns.route("/logout")
class Logout(Resource):
    @ns.response(200, "Session cleared")
    def post(self):
        """Sign out."""
        user = session.pop("user", None)
        return {"message": "Successfully logged out" if user else "No user logged in"}, 200
