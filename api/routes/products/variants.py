"""The colour sets a product is offered in."""

import uploads
from db import get_db_connection
from api.models.catalog import variant_list_model, variant_model, variant_write_model
from api.routes.crud import CREATED
from api.routes.products import ns
from api.security import PROTECTED_DOC, auth_required
from repositories import (
    ColorSetRepository,
    ProductRepository,
    ProductVariantRepository,
)
from flask_restx import Resource


@ns.route("/<int:product_id>/variants")
@ns.param("product_id", "The product identifier")
class ProductVariantList(Resource):
    @ns.marshal_with(variant_list_model)
    @ns.response(200, "The product's variants")
    @ns.response(404, "Product not found")
    def get(self, product_id):
        """List the colour sets this product is offered in."""
        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            return {
                "variants": ProductVariantRepository(cursor).list_for_product(
                    product_id
                )
            }

    @ns.expect(variant_write_model, validate=True)
    @ns.marshal_with(variant_model, code=CREATED)
    @ns.response(201, "Variant created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Product or colour set not found")
    @ns.response(409, "This product already has a variant in that colour set")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self, product_id):
        """Offer this product in another colour set."""
        color_set_id = ns.payload["color_set_id"]

        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            if not ColorSetRepository(cursor).exists(color_set_id):
                ns.abort(404, f"The colour set #{color_set_id} does not exist.")

            variants = ProductVariantRepository(cursor)
            if variants.exists_for_color_set(product_id, color_set_id):
                ns.abort(
                    409,
                    f"Product #{product_id} already has a variant in colour set "
                    f"#{color_set_id}.",
                )

            variant_id = variants.create(
                product_id=product_id, color_set_id=color_set_id
            )
            return variants.get(variant_id), 201


@ns.route("/<int:product_id>/variants/<int:variant_id>")
@ns.param("product_id", "The product identifier")
@ns.param("variant_id", "The variant identifier")
class ProductVariant(Resource):
    @ns.marshal_with(variant_model)
    @ns.response(200, "The deleted variant")
    @ns.response(404, "Product not found, or the variant is not one of its own")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, product_id, variant_id):
        """Stop offering this product in one colour set."""
        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            variants = ProductVariantRepository(cursor)
            if not variants.belongs_to(variant_id, product_id):
                ns.abort(
                    404,
                    f"Variant #{variant_id} does not belong to product #{product_id}",
                )

            variant = variants.get(variant_id)
            # The rows of this colour's photographs go with it — a soft-deleted
            # child of a deleted parent is a state nothing could present. The
            # files stay until the sweep.
            variants.delete(variant_id)
            return variant, 200
