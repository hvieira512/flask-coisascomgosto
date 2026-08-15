"""Error pages for the site, JSON errors for the API.

Handlers are registered app-wide rather than on the blueprint: Flask only routes
a 404 to a blueprint handler when the URL matched that blueprint, and an unknown
URL matches nothing. `register` is called once from web/__init__.py.
"""

from flask import jsonify, render_template, request


def _wants_json() -> bool:
    """API clients get JSON errors; browsers get the rendered error pages."""
    return request.path.startswith("/api")


def not_found(error):
    """Custom 404 page for the site, JSON for the API."""
    if _wants_json():
        return jsonify({"message": "Resource not found"}), 404

    return render_template("errors/404.html"), 404


def server_error(error):
    """Custom 500 page for the site, JSON for the API."""
    if _wants_json():
        return jsonify({"message": "Internal server error"}), 500

    return render_template("errors/500.html"), 500


def register(app):
    """Attach the error handlers to an application."""
    app.register_error_handler(404, not_found)
    app.register_error_handler(500, server_error)
