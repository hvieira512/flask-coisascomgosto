"""The guard on every write endpoint.

Authentication is Flask's session cookie, which the browser attaches to page
loads and fetch() alike. Unlike the dashboard's page-level guard, which
redirects a visitor to the login form, this one answers 401 with JSON: its
callers are fetch() requests, and a redirect would hand them a login page to
parse as a product.
"""

from functools import wraps

from flask import session
from flask_restx import abort

PROTECTED_DOC = {
    "responses": {
        401: "Not signed in",
    },
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            abort(401, "Authentication is required.")
        return view(*args, **kwargs)

    return wrapped
