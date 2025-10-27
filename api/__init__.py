from flask_restx import Api

from .routes.categories import ns as categories_ns
from .routes.users import ns as users_ns
from .routes.auth import ns as auth_ns
from .routes.products import ns as products_ns

api = Api(
    title="CoisasComGosto API",
    version="1.0",
    description="CoisasComGosto API",
    prefix="/api",
    doc="/api/docs",
)

api.add_namespace(categories_ns, path="/categories")
api.add_namespace(users_ns, path="/users")
api.add_namespace(auth_ns, path="/auth")
api.add_namespace(products_ns, path="/products")
