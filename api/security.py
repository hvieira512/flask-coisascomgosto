"""Bearer-token helpers shared by the protected namespaces."""

from functools import wraps

from flask_jwt_extended import get_jwt, jwt_required
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
        401: "Missing, malformed or expired access token",
    },
}


def token_required(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        if not get_jwt().get("is_admin"):
            abort(403, "Administrator privileges are required.")
        return view(*args, **kwargs)

    return wrapped
