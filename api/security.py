"""The guard on every write endpoint.

Two kinds of caller reach these endpoints, so two credentials are accepted:

    Authorization: Bearer <access_token>    an API client
    the Flask session cookie                the dashboard's own fetch() calls

A bearer token is the API's documented mechanism — POST /auth/login for a pair,
/auth/refresh when the access token expires — and it is what Swagger's Authorize
button sends. The session is what the server-rendered dashboard pages already
hold, so its scripts need no token handling of their own.

Either way the answer on failure is 401 with JSON, never a redirect: the callers
are fetch() requests and API clients, and a redirect would hand them a login
page to parse as a payload.
"""

from functools import wraps

from flask import session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_restx import abort

# Renders the Authorize button in /api/docs.
AUTHORIZATIONS = {
    "Bearer": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Paste: Bearer &lt;access_token&gt;",
    }
}

# Applied to protected resources so the padlock and the 401 show up in Swagger.
PROTECTED_DOC = {
    "security": "Bearer",
    "responses": {
        401: "Missing, malformed or expired access token, and no session",
    },
}


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            # Raises through flask-jwt-extended's own handlers, which answer 401
            # for an expired token and 422 for a malformed one.
            verify_jwt_in_request()
        return view(*args, **kwargs)

    return wrapped


def current_user_id():
    """The caller's user id, from whichever credential they presented."""
    if "user" in session:
        return session["user"]["id"]

    identity = get_jwt_identity()
    return int(identity) if identity is not None else None
