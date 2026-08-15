"""The rendered site: storefront, login and dashboard.

`register_web(app)` is the single entrypoint app.py calls. It mounts the
blueprints and attaches the pieces that must live on the application object
rather than on a blueprint — template filters and error handlers.
"""

from flask import Blueprint, redirect, session, url_for

from . import errors, filters
from .auth import bp as auth_bp
from .dashboard import bp as dashboard_bp
from .store import bp as store_bp

web_bp = Blueprint("web", __name__)

web_bp.register_blueprint(auth_bp)
web_bp.register_blueprint(dashboard_bp)
web_bp.register_blueprint(store_bp)


@web_bp.app_context_processor
def inject_contact():
    """Make the shop's contact details available to every template.

    The navbar and footer render social links and the address from it, so it is
    injected app-wide rather than passed from each view. A missing table (before
    init-db has run) must not break page rendering, hence the guard.
    """
    from api.db import get_db_connection
    from api.repositories import ContactRepository

    try:
        with get_db_connection() as (_, cursor):
            return {"contact": ContactRepository(cursor).get() or {}}
    except Exception:
        return {"contact": {}}


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.store.home"))


def register_web(app):
    """Mount the site on an application: blueprints, filters, error pages."""
    app.register_blueprint(web_bp)
    filters.register(app)
    errors.register(app)
