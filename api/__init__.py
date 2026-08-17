"""The REST API.

Namespaces are mounted under /api, with interactive Swagger docs at /api/docs
and the raw schema at /api/swagger.json.

Layering:
    routes/         HTTP concerns only: validation, status codes, marshalling
    models/         flask-restx marshalling models, which also define the docs
    repositories/   every SQL statement in the application
    db.py           connection handling and schema initialisation
    pagination.py   request-arg parsing and the pagination response envelope
    security.py     the session guard applied to every write
"""

from flask_restx import Api

from .routes.auth import ns as auth_ns
from .routes.categories import ns as categories_ns
from .routes.collections import ns as collections_ns
from .routes.color_sets import ns as color_sets_ns
from .routes.contacts import ns as contacts_ns
from .routes.events import ns as events_ns
from .routes.colors import ns as colors_ns
from .routes.product_types import ns as product_types_ns
from .routes.products import ns as products_ns
from .routes.sizes import ns as sizes_ns
from .routes.users import ns as users_ns

api = Api(
    title="CoisasComGosto API",
    version="2.0",
    description=(
        "Catalog API for CoisasComGosto.\n\n"
        "A product has a required **category** and may also have a **product "
        "type** (with one level of sub-types), belong to a **collection**, "
        "declare a **default size**, list the **sizes** it is available in, and "
        "carry **variants** — one per **colour set** it is offered in.\n\n"
        "Catalog reads are public. Every write, plus `/users` and `/contacts`, "
        "requires a signed-in session: POST `/auth/login`, and the session "
        "cookie you get back rides along on subsequent calls."
    ),
    prefix="/api",
    doc="/api/docs",
)

api.add_namespace(categories_ns, path="/categories")
api.add_namespace(product_types_ns, path="/product-types")
api.add_namespace(collections_ns, path="/collections")
api.add_namespace(colors_ns, path="/colors")
api.add_namespace(color_sets_ns, path="/color-sets")
api.add_namespace(sizes_ns, path="/sizes")
api.add_namespace(products_ns, path="/products")
api.add_namespace(contacts_ns, path="/contacts")
api.add_namespace(events_ns, path="/events")
api.add_namespace(users_ns, path="/users")
api.add_namespace(auth_ns, path="/auth")
