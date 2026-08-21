from flask import Blueprint, render_template

from db import get_db_connection
from repositories import EventRepository, ProductTypeRepository

bp = Blueprint("store", __name__)

# Seven families and the "ver tudo" tile fill two rows of four. The landing page
# is a way into the catalogue rather than a copy of it, but the tiles are now
# photographs rather than cards and the whole range fits.
TYPES_LIMIT = 7
TIMELINE_LIMIT = 12


@bp.route("/")
def home():
    with get_db_connection() as (_, cursor):
        types = ProductTypeRepository(cursor)
        product_types = types.list(limit=TYPES_LIMIT, offset=0)
        ids = [t["id"] for t in product_types]
        covers = types.cover_images(ids)
        counts = types.product_counts(ids)
        for product_type in product_types:
            product_type["cover"] = covers.get(product_type["id"])
            product_type["count"] = counts.get(product_type["id"], 0)

        events = EventRepository(cursor).list(limit=TIMELINE_LIMIT, offset=0)

    return render_template(
        "store/home.html",
        product_types=product_types,
        events=events,
    )


@bp.route("/products")
def products():
    return render_template("store/products.html")


@bp.route("/products/<int:product_id>")
def product(product_id):
    return render_template("store/product.html", product_id=product_id)
