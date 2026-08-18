from flask import Blueprint, render_template

from api.db import get_db_connection
from api.repositories import EventRepository, ProductTypeRepository

bp = Blueprint("store", __name__)

TYPES_LIMIT = 12
TIMELINE_LIMIT = 12


@bp.route("/")
def home():
    with get_db_connection() as (_, cursor):
        types = ProductTypeRepository(cursor)
        product_types = types.list(roots_only=True, limit=TYPES_LIMIT, offset=0)
        covers = types.cover_images([t["id"] for t in product_types])
        for product_type in product_types:
            product_type["cover"] = covers.get(product_type["id"])

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
