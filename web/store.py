"""Public storefront: landing page, product catalog and individual products.

The catalog and product pages are server-rendered shells whose data is fetched
from the JSON API by static/js/store/*.js. The landing page is rendered with a
handful of featured products so it has content even with JavaScript disabled.
"""

from flask import Blueprint, render_template

from api.db import get_db_connection
from api.repositories import EventRepository, ProductTypeRepository

bp = Blueprint("store", __name__)

TYPES_LIMIT = 12
TIMELINE_LIMIT = 12


@bp.route("/")
def home():
    """Landing page: hero, the story, what we make, the timeline and contacts.

    Only top-level types are listed. Sub-types describe how one object is
    finished ("Coracao" hung on a string vs. standing as a base), which is a
    distinction for the catalog filters, not for a first look at the range.
    """
    with get_db_connection() as (_, cursor):
        product_types = ProductTypeRepository(cursor).list(
            roots_only=True, limit=TYPES_LIMIT, offset=0
        )
        events = EventRepository(cursor).list(limit=TIMELINE_LIMIT, offset=0)

    return render_template(
        "store/home.html",
        product_types=product_types,
        events=events,
    )


@bp.route("/products")
def products():
    """Catalog: filter sidebar plus a product grid."""
    return render_template("store/products.html")


@bp.route("/products/<int:product_id>")
def product(product_id):
    """One product: image previewer, thumbnail carousel and details."""
    return render_template("store/product.html", product_id=product_id)
