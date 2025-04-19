from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
def index():
    return redirect(url_for("web.dashboard.home"))


@bp.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("web.auth.home"))

    return render_template("dashboard/home.html")


@bp.route("/products")
def products():
    if "username" not in session:
        return redirect(url_for("web.auth.home"))

    return render_template("dashboard/products.html")


@bp.route("/stats")
def stats():
    if "username" not in session:
        return redirect(url_for("web.auth.home"))

    return render_template("dashboard/stats.html")
