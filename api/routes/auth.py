"""Authentication.

The API uses JWT bearer tokens:

    POST /auth/login    -> { access_token, refresh_token, user }
    POST /auth/refresh  -> { access_token }   (send the REFRESH token)
    GET  /auth/me       -> the caller's own user record
    POST /auth/logout   -> clears the server-rendered session

Access tokens are short-lived; when one expires the client exchanges its
refresh token at /auth/refresh rather than asking for the password again.

The server-rendered dashboard still uses the Flask session, so login populates
both: the session for the HTML pages and the tokens for API clients.
"""

from flask import session
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from flask_restx import Namespace, Resource
from werkzeug.security import check_password_hash, generate_password_hash

from api.db import get_db_connection
from api.models.auth import login_model, refresh_model, token_model
from api.models.users import user_model
from api.repositories import UserRepository
from api.security import PROTECTED_DOC, token_required
from api.utils import is_email_valid

ns = Namespace("auth", description="Authentication operations")

for model in [login_model, refresh_model, token_model, user_model]:
    ns.models[model.name] = model

# Registration keeps its own model name, declared in api/models/auth.py.
from api.models.auth import register_model  # noqa: E402

ns.models[register_model.name] = register_model


def _issue_tokens(user: dict) -> dict:
    """Build the token pair for a user.

    The identity is the user ID as a string (a JWT `sub` must be a string);
    is_admin rides along as a claim so guards do not need a database round
    trip on every request.
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

        if not is_email_valid(email):
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
        username = data["username"]
        password = data["password"]

        with get_db_connection() as (_, cursor):
            credentials = UserRepository(cursor).get_credentials(username)
            if not credentials:
                ns.abort(404, "User invalid.")

            if not check_password_hash(credentials["password"], password):
                ns.abort(401, "Invalid login.")

            user = {k: v for k, v in credentials.items() if k != "password"}

            # The server-rendered dashboard authenticates by session, so keep
            # populating it alongside the tokens.
            session["user"] = user

            return _issue_tokens(user), 200


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
    def post(self):
        """Exchange a refresh token for a new access token.

        This is what a client calls when its access token expires, instead of
        prompting for the password again. The refresh token is unchanged and
        keeps its original expiry.
        """
        from flask_jwt_extended import jwt_required

        @jwt_required(refresh=True)
        def _refresh():
            user_id = get_jwt_identity()

            with get_db_connection() as (_, cursor):
                user = UserRepository(cursor).get(int(user_id))
                if not user:
                    ns.abort(401, "The account for this token no longer exists.")

                claims = {
                    "username": user["username"],
                    "is_admin": user["is_admin"],
                }
                return {
                    "access_token": create_access_token(
                        identity=str(user["id"]), additional_claims=claims
                    ),
                    "refresh_token": None,
                    "user": user,
                }, 200

        return _refresh()


@ns.route("/me")
class Me(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(user_model)
    @ns.response(200, "The authenticated user")
    @token_required
    def get(self):
        """Return the account the access token belongs to."""
        user_id = get_jwt_identity()

        with get_db_connection() as (_, cursor):
            user = UserRepository(cursor).get(int(user_id))
            if not user:
                ns.abort(401, "The account for this token no longer exists.")

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
        msg = "Successfully logged out" if user else "No user logged in"
        return {"message": msg}, 200
