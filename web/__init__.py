from flask import Blueprint, redirect, url_for

from .home import home_bp

web_bp = Blueprint("web", __name__)

web_bp.register_blueprint(home_bp)


@web_bp.route("/")
def index():
    return redirect(url_for("web.home.home"))
