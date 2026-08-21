"""Authentication.

    POST /auth/register -> a new account
    POST /auth/login    -> { access_token, refresh_token, user }
    POST /auth/refresh  -> { access_token }   (send the REFRESH token)
    GET  /auth/me       -> the caller's own user record
    POST /auth/logout   -> clears the server-rendered session

Access tokens are short-lived; when one expires the client exchanges its refresh
token at /auth/refresh rather than asking for the password again.

Login also populates the Flask session, because the server-rendered dashboard
pages are gated by it — a page load cannot carry a token from localStorage. So
the tokens serve API clients and the cookie serves the rendered pages, and
api/security.py accepts either.
"""

import re

from flask import session
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_restx import Namespace, Resource
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection
from api.models.auth import login_model, refresh_model, register_model, token_model
from api.models.users import user_model
from api.routes.crud import bail
from repositories import UserRepository
from api.security import PROTECTED_DOC, auth_required, current_user_id

ns = Namespace("auth", description="Authentication operations")

for model in [login_model, register_model, refresh_model, token_model, user_model]:
    ns.models[model.name] = model

# Deliberately loose: this rejects typos, not exotic-but-valid addresses. The
# only real proof an address works is sending to it.
EMAIL = re.compile(r"([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Za-z]{2,})+")


def _tokens_for(user: dict) -> dict:
    """The token pair for a user.

    The identity is the user id as a string, because a JWT `sub` must be one.
    is_admin rides along as a claim so a guard needs no database round trip.
    """
    identity = str(user["id"])
    claims = {"username": user["username"], "is_admin": user["is_admin"]}

    return {
        "access_token": create_access_token(identity=identity, additional_claims=claims),
        "refresh_token": create_refresh_token(
            identity=identity, additional_claims=claims
        ),
        "user": user,
    }


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
    @ns.marshal_with(token_model)
    @ns.response(200, "Access and refresh tokens")
    @ns.response(401, "Invalid password")
    @ns.response(404, "Unknown username")
    def post(self):
        """Exchange a username and password for a token pair."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            credentials = UserRepository(cursor).get_credentials(data["username"])
            if not credentials:
                bail(ns, 404, "User invalid.")

            if not check_password_hash(credentials["password"], data["password"]):
                ns.abort(401, "Invalid login.")

            user = {k: v for k, v in credentials.items() if k != "password"}

            # The rendered dashboard authenticates by session, so keep
            # populating it alongside the tokens.
            session["user"] = user

            return _tokens_for(user), 200


@ns.route("/refresh")
class Refresh(Resource):
    @ns.expect(refresh_model)
    @ns.doc(
        security="Bearer",
        description="Send the REFRESH token in the Authorization header.",
    )
    @ns.marshal_with(token_model)
    @ns.response(200, "A fresh access token")
    @ns.response(401, "Missing, malformed or expired refresh token")
    @jwt_required(refresh=True)
    def post(self):
        """Exchange a refresh token for a new access token.

        This is what a client calls when its access token expires, instead of
        prompting for the password again. The refresh token itself is unchanged
        and keeps its original expiry, so it is not reissued here.
        """
        with get_db_connection() as (_, cursor):
            user = UserRepository(cursor).get(int(get_jwt_identity()))
            if not user:
                bail(ns, 401, "The account for this token no longer exists.")

            claims = {"username": user["username"], "is_admin": user["is_admin"]}
            return {
                "access_token": create_access_token(
                    identity=str(user["id"]), additional_claims=claims
                ),
                "refresh_token": None,
                "user": user,
            }, 200


@ns.route("/me")
class Me(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(user_model)
    @ns.response(200, "The authenticated user")
    @auth_required
    def get(self):
        """Return the account the caller is authenticated as."""
        with get_db_connection() as (_, cursor):
            user_id = current_user_id()
            user = UserRepository(cursor).get(user_id) if user_id is not None else None
            if not user:
                session.clear()
                bail(ns, 401, "This account no longer exists.")

            return user


@ns.route("/logout")
class Logout(Resource):
    @ns.response(200, "Session cleared")
    def post(self):
        """Clear the server-rendered session.

        JWTs are stateless, so the tokens themselves stay valid until they
        expire — the client is responsible for discarding them.
        """
        user = session.pop("user", None)
        return {"message": "Successfully logged out" if user else "No user logged in"}, 200
