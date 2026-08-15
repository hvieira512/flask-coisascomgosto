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
    from api.db import get_db_connection
    from api.repositories import ContactRepository

    try:
        with get_db_connection() as (_, cursor):
            return {"contact": ContactRepository(cursor).get() or {}}
    except Exception:
        # Before init-db has run there is no table; pages must still render.
        return {"contact": {}}


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.store.home"))


def register_web(app):
    app.register_blueprint(web_bp)
    filters.register(app)
    errors.register(app)
