from flask import Blueprint, redirect, session, url_for

from .home import bp as home_bp
from .auth import bp as auth_bp
from .dashboard import bp as dashboard_bp

web_bp = Blueprint("web", __name__)

web_bp.register_blueprint(home_bp)
web_bp.register_blueprint(auth_bp)
web_bp.register_blueprint(dashboard_bp)


@web_bp.route("/")
def home():
    return redirect(url_for("web.home.home"))


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.home.home"))
