"""The dashboard's pages.

Each one is a shell: the template renders the chrome and an empty container, and
the page's own module fills it from the API. So there is nothing here but the
guard and the render_templates.
"""

from flask import Blueprint, redirect, render_template, session, url_for

from db import get_db_connection
from repositories.base import one_row

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.context_processor
def rail_counts():
    """What the rail says beside each section.

    One query for all four: they are four numbers on the chrome of every page, and
    four round trips for them would be four more than the chrome deserves.
    """
    with get_db_connection() as (_, cursor):
        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM products) AS pieces,"
            "       (SELECT COUNT(*) FROM color_sets) AS color_sets,"
            "       (SELECT COUNT(*) FROM collections) AS collections,"
            "       (SELECT COUNT(*) FROM events) AS events"
        )
        return {"counts": one_row(cursor)}


@bp.before_request
def require_login():
    """Anonymous visitors go to the login page.

    On the blueprint rather than on each view: a decorator per route means the
    seventh page can be added without one and nobody notices until it is public.
    """
    if "user" not in session:
        return redirect(url_for("web.auth.home"))


@bp.route("/")
def index():
    return redirect(url_for("web.dashboard.home"))


@bp.route("/home")
def home():
    return render_template("dashboard/home.html")


@bp.route("/products")
def products():
    return render_template("dashboard/products.html")


@bp.route("/events")
def events():
    return render_template("dashboard/events.html")


@bp.route("/types")
def types():
    return render_template("dashboard/types.html")


@bp.route("/colors")
def colors():
    return render_template("dashboard/colors.html")


@bp.route("/collections")
def collections():
    return render_template("dashboard/collections.html")


@bp.route("/contacts")
def contacts():
    return render_template("dashboard/contacts.html")
