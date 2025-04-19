from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


# ----------------
# Helper functions
# ----------------


def check_session():
    if "username" not in session:
        return redirect(url_for("web.auth.home"))


def check_admin():
    if session["admin"] is not True:
        return redirect(url_for("web.dashboard.home"))


# ----------------
# Route handlers
# ----------------


@bp.route("/")
def index():
    check_session()
    return redirect(url_for("web.dashboard.home"))


@bp.route("/home")
def home():
    check_session()
    return render_template("dashboard/home.html")


@bp.route("/products")
def products():
    check_session()
    return render_template("dashboard/products.html")


@bp.route("/stats")
def stats():
    check_session()
    return render_template("dashboard/stats.html")


@bp.route("/profile")
def profile():
    check_session()
    return render_template("dashboard/profile.html")


@bp.route("/settings")
def settings():
    check_session()
    return render_template("dashboard/settings.html")
