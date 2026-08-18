from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def login_required(view):
    """Redirect anonymous visitors to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("web.auth.home"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/")
@login_required
def index():
    return redirect(url_for("web.dashboard.home"))


@bp.route("/home")
@login_required
def home():
    return render_template("dashboard/home.html")


@bp.route("/products")
@login_required
def products():
    return render_template("dashboard/products.html")


@bp.route("/events")
@login_required
def events():
    return render_template("dashboard/events.html")


@bp.route("/types")
@login_required
def types():
    return render_template("dashboard/types.html")


@bp.route("/contacts")
@login_required
def contacts():
    return render_template("dashboard/contacts.html")
