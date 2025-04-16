from flask import Blueprint, render_template

bp = Blueprint("home", __name__)


@bp.route("/home")
def home():
    return render_template("home/index.html")
