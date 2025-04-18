from flask import Blueprint, redirect, render_template, session, url_for

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
def home():
    if "username" not in session:
        return redirect(url_for("web.auth.home"))

    return render_template("dashboard/index.html")
