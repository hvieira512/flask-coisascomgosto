from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


# ----------------
# Helper functions
# ----------------


def login_required(view):
    """Redirect anonymous visitors to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("web.auth.home"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Redirect non-admin users back to the dashboard home."""

    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session["user"].get("is_admin"):
            return redirect(url_for("web.dashboard.home"))
        return view(*args, **kwargs)

    return wrapped


# ----------------
# Route handlers
# ----------------


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


@bp.route("/profile")
@login_required
def profile():
    return render_template("dashboard/profile.html")


@bp.route("/settings")
@login_required
def settings():
    return render_template("dashboard/settings.html")
