"""The REST API.

Namespaces are mounted under /api, with interactive Swagger docs at /api/docs
and the raw schema at /api/swagger.json.

Layering:
    routes/         HTTP concerns only: validation, status codes, marshalling
    models/         flask-restx marshalling models, which also define the docs
    repositories/   every SQL statement in the application
    db.py           connection handling and schema initialisation
    pagination.py   request-arg parsing and the pagination response envelope
    security.py     auth_required — bearer token or session — on every write
"""

from flask_restx import Api

from api.security import AUTHORIZATIONS

from .routes.auth import ns as auth_ns
from .routes.collections import ns as collections_ns
from .routes.color_sets import ns as color_sets_ns
from .routes.contacts import ns as contacts_ns
from .routes.events import ns as events_ns
from .routes.materials import ns as materials_ns
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
        "A product has a required **product type** and may also name a "
        "**material**, belong to a **collection**, "
        "declare a **default size**, list the **sizes** it is available in, and "
        "carry **variants** — one per **colour set** it is offered in.\n\n"
        "Catalog reads are public. Every write, plus `/users` and `/contacts`, "
        "needs a **bearer token**: POST `/auth/login` for a token pair, then "
        "`/auth/refresh` when the access token expires. Use the **Authorize** "
        "button above to send it from these docs."
    ),
    prefix="/api",
    doc="/api/docs",
    authorizations=AUTHORIZATIONS,
)

api.add_namespace(product_types_ns, path="/product-types")
api.add_namespace(materials_ns, path="/materials")
api.add_namespace(collections_ns, path="/collections")
api.add_namespace(colors_ns, path="/colors")
api.add_namespace(color_sets_ns, path="/color-sets")
api.add_namespace(sizes_ns, path="/sizes")
api.add_namespace(products_ns, path="/products")
api.add_namespace(contacts_ns, path="/contacts")
api.add_namespace(events_ns, path="/events")
api.add_namespace(users_ns, path="/users")
api.add_namespace(auth_ns, path="/auth")
