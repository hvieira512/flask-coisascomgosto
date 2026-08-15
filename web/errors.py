from flask import jsonify, render_template, request


def _wants_json():
    return request.path.startswith("/api")


def not_found(error):
    if _wants_json():
        return jsonify({"message": "Resource not found"}), 404
    return render_template("errors/404.html"), 404


def server_error(error):
    if _wants_json():
        return jsonify({"message": "Internal server error"}), 500
    return render_template("errors/500.html"), 500


def register(app):
    # App-wide, not on the blueprint: an unknown URL matches no blueprint, so a
    # blueprint-level 404 handler would never fire.
    app.register_error_handler(404, not_found)
    app.register_error_handler(500, server_error)
