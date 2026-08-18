"""The sizes a product is available in."""

from api.db import get_db_connection
from api.models.catalog import product_sizes_write_model, size_model
from api.routes.products import ns
from api.security import PROTECTED_DOC, auth_required
from api.repositories import ProductRepository, SizeRepository
from flask_restx import Resource


@ns.route("/<int:product_id>/sizes")
@ns.param("product_id", "The product identifier")
class ProductSizes(Resource):
    @ns.marshal_list_with(size_model)
    @ns.response(200, "The sizes this product is available in")
    @ns.response(404, "Product not found")
    def get(self, product_id):
        """List the sizes this product is available in."""
        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)
            if not products.exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            return products.get_sizes(product_id)

    @ns.expect(product_sizes_write_model, validate=True)
    @ns.marshal_list_with(size_model)
    @ns.response(200, "The product's sizes after the replacement")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Product or size not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, product_id):
        """Replace the set of sizes this product is available in.

        Send an empty list to mark the product as sold only in its default size.
        """
        size_ids = ns.payload["size_ids"]

        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)
            if not products.exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            missing = SizeRepository(cursor).missing_ids(size_ids)
            if missing:
                ns.abort(404, f"Unknown size IDs: {sorted(missing)}")

            products.set_sizes(product_id, size_ids)
            return products.get_sizes(product_id)
