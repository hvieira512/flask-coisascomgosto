from flask import Blueprint, redirect, url_for

from .home import bp as home_bp
from .auth import bp as auth_bp

web_bp = Blueprint("web", __name__)

web_bp.register_blueprint(home_bp)
web_bp.register_blueprint(auth_bp)


@web_bp.route("/")
def index():
    return redirect(url_for("web.home.home"))
