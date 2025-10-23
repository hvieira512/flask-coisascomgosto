from flask import Blueprint
from flask_restx import Api

from .routes.categories import ns as categories_ns

api_bp = Blueprint("api", __name__, url_prefix="/api")

api = Api(
    api_bp,
    title="CoisasComGosto API",
)

api.add_namespace(categories_ns, path="/categories")
