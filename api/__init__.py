from flask import Blueprint

from .categories import bp as categories_bp
from .products import bp as products_bp
from .users import bp as users_bp

api_bp = Blueprint("api", __name__, url_prefix="/api")

api_bp.register_blueprint(categories_bp, url_prefix="/categories")
api_bp.register_blueprint(products_bp, url_prefix="/products")
api_bp.register_blueprint(users_bp, url_prefix="/users")
