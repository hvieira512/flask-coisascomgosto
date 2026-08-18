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
    """The shop's own details, on every rendered page: the footer and the landing
    page's contact cards read them.

    The one failure worth swallowing is the table not existing yet, between a
    clone and the first init-db — a page still has to render, or the person
    setting the project up sees a stack trace instead of a shop. Anything else,
    a server that is down or a query that is wrong, propagates: a shop quietly
    serving no contact details at all is worse than an error that says so.
    """
    from pymysql.constants import ER
    from pymysql.err import ProgrammingError

    from db import get_db_connection
    from repositories import ContactRepository

    try:
        with get_db_connection() as (_, cursor):
            return {"contact": ContactRepository(cursor).get() or {}}
    except ProgrammingError as error:
        if error.args and error.args[0] == ER.NO_SUCH_TABLE:
            return {"contact": {}}
        raise


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.store.home"))


def register_web(app):
    app.register_blueprint(web_bp)
    filters.register(app)
    errors.register(app)
