"""JWT helpers shared by the protected namespaces.

The API authenticates with bearer tokens: POST /api/auth/login returns a
short-lived access token plus a long-lived refresh token, and
POST /api/auth/refresh exchanges the refresh token for a fresh access token.

Swagger's "Authorize" button is wired to the same header, so protected
endpoints can be tried from /api/docs.
"""

from functools import wraps

from flask_jwt_extended import get_jwt, jwt_required
from flask_restx import abort

# Advertised on the Api object so /api/docs renders an Authorize button.
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
        401: "Missing, malformed or expired access token",
    },
}


def token_required(view):
    """Require a valid access token.

    Thin wrapper over flask-jwt-extended's jwt_required so route modules do
    not each have to repeat the import and the Swagger annotation.
    """

    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Require a valid access token belonging to an administrator."""

    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        if not get_jwt().get("is_admin"):
            abort(403, "Administrator privileges are required.")
        return view(*args, **kwargs)

    return wrapped
