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

Accepting the cookie is what makes CSRF possible, so a session-authenticated
write additionally has to prove it came from our own code — see REQUIRED_HEADER.
"""

from functools import wraps
from typing import Optional

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_restx import abort

# flask-restx names its own backport of HTTPStatus in abort()'s signature, so a
# plain 403 is the wrong type to a checker while working fine at runtime. See the
# longer note on CREATED in api/routes/crud.py.
from flask_restx._http import HTTPStatus

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
        403: "Session-authenticated write without the X-Requested-With header",
    },
}

# The CSRF defence for session-authenticated writes. Its *value* is irrelevant;
# what matters is that a header outside the CORS-safelist cannot be set by a
# cross-site HTML form at all, and a cross-site fetch() that sets one turns the
# request into a preflight this API does not answer. So only same-origin code can
# produce it, which is the property we need.
#
# The alternative was a CSRF token, which needs a mint, a place to keep it and a
# rotation story to protect two endpoints. This is one header.
REQUIRED_HEADER = "X-Requested-With"

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        # A read needs the cookie and nothing else: cross-site GETs cannot be
        # read back, so there is nothing to protect and no reason to reject a
        # dashboard whose token happens to be stale.
        if "user" in session and (
            request.method in SAFE_METHODS or REQUIRED_HEADER in request.headers
        ):
            return view(*args, **kwargs)

        # A session-authenticated write with no header falls through to the token,
        # so Swagger's Authorize button still works from a browser that also holds
        # a dashboard session. Without a token there is nothing left to check, and
        # 403 says which of the two things is missing — verify_jwt_in_request()
        # would answer "Missing Authorization Header", which is not the point.
        if "user" in session and "Authorization" not in request.headers:
            # This is the cross-site POST. The uploads were the live exposure:
            # multipart/form-data is a content type an HTML form can send with no
            # preflight, so nothing else stood in its way.
            abort(
                HTTPStatus.FORBIDDEN,
                f"{REQUIRED_HEADER} header required for session-authenticated writes",
            )

        # Raises through flask-jwt-extended's own handlers, which answer 401 for
        # an expired token and 422 for a malformed one.
        verify_jwt_in_request()
        return view(*args, **kwargs)

    return wrapped


def current_user_id() -> Optional[int]:
    """The caller's user id, from whichever credential they presented.

    Optional because both branches can come up empty — no session and no token —
    even though every caller sits behind @auth_required. The one caller checks,
    which costs a line and means the guard is in the code rather than in trust.
    """
    if "user" in session:
        return session["user"]["id"]

    identity = get_jwt_identity()
    return int(identity) if identity is not None else None
