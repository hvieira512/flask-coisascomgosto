"""Photographs of a product, uploaded or referenced by path."""

from flask import request
from flask_restx import Resource
from werkzeug.datastructures import FileStorage

import uploads
from db import get_db_connection
from api.models.catalog import image_model, image_write_model
from api.routes.products import ns
from api.security import PROTECTED_DOC, auth_required
from repositories import (
    ProductImageRepository,
    ProductRepository,
    ProductVariantRepository,
)


upload_parser = ns.parser()
upload_parser.add_argument(
    "file", location="files", type=FileStorage, required=True,
    help="Photograph: jpg, png or webp, up to 5 MB",
)
upload_parser.add_argument(
    "variant_id", location="form", type=int, required=False,
    help="Pin the photograph to one colour set; omit for a product-wide one",
)
upload_parser.add_argument("alt", location="form", required=False)


@ns.route("/<int:product_id>/images")
@ns.param("product_id", "The product identifier")
class ProductImageList(Resource):
    @ns.marshal_list_with(image_model)
    @ns.param("variant_id", "Only images attached to this variant")
    @ns.response(200, "The product's images, in display order")
    @ns.response(404, "Product not found")
    def get(self, product_id):
        """List a product's images, optionally narrowed to one variant."""
        variant_id = request.args.get("variant_id", type=int)

        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            return ProductImageRepository(cursor).list_for_product(
                product_id, variant_id=variant_id
            )

    @ns.expect(image_write_model, validate=True)
    @ns.marshal_with(image_model, code=201)
    @ns.response(201, "Image added")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Product not found, or the variant is not one of its own")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self, product_id):
        """Add an image to a product, or to one of its variants."""
        data = ns.payload
        variant_id = data.get("variant_id")

        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            if variant_id is not None and not ProductVariantRepository(
                cursor
            ).belongs_to(variant_id, product_id):
                ns.abort(
                    404,
                    f"Variant #{variant_id} does not belong to product #{product_id}",
                )

            images = ProductImageRepository(cursor)
            image_id = images.create(
                product_id=product_id,
                url=data["url"],
                alt=data.get("alt"),
                variant_id=variant_id,
                position=data.get("position") or 0,
            )
            return images.get(image_id), 201


@ns.route("/<int:product_id>/images/upload")
@ns.param("product_id", "The product identifier")
class ProductImageUpload(Resource):
    @ns.expect(upload_parser)
    @ns.marshal_with(image_model, code=201)
    @ns.response(201, "Photograph stored and attached")
    @ns.response(400, "Missing file, unsupported format, or too large")
    @ns.response(404, "Product not found, or the variant is not one of its own")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self, product_id):
        """Upload a photograph and attach it to a product or one of its variants."""
        args = upload_parser.parse_args()
        variant_id = args.get("variant_id")

        with get_db_connection() as (_, cursor):
            if not ProductRepository(cursor).exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            if variant_id is not None and not ProductVariantRepository(
                cursor
            ).belongs_to(variant_id, product_id):
                ns.abort(
                    404,
                    f"Variant #{variant_id} does not belong to product #{product_id}",
                )

            try:
                url = uploads.save(args["file"])
            except uploads.UploadError as error:
                ns.abort(400, str(error))
                # ns.abort raises, but its signature does not say so, so without
                # this the URL below reads as possibly unbound.
                raise

            images = ProductImageRepository(cursor)
            image_id = images.create(
                product_id=product_id,
                url=url,
                alt=args.get("alt"),
                variant_id=variant_id,
            )
            return images.get(image_id), 201


@ns.route("/<int:product_id>/images/<int:image_id>")
@ns.param("product_id", "The product identifier")
@ns.param("image_id", "The image identifier")
class ProductImage(Resource):
    @ns.expect(image_write_model, validate=True)
    @ns.marshal_with(image_model)
    @ns.response(200, "Image updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Image or variant does not belong to this product")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, product_id, image_id):
        """Update an image's URL, alt text, position or variant."""
        data = ns.payload
        variant_id = data.get("variant_id")

        with get_db_connection() as (_, cursor):
            images = ProductImageRepository(cursor)

            if not images.belongs_to(image_id, product_id):
                ns.abort(
                    404,
                    f"Image #{image_id} does not belong to product #{product_id}",
                )

            if variant_id is not None and not ProductVariantRepository(
                cursor
            ).belongs_to(variant_id, product_id):
                ns.abort(
                    404,
                    f"Variant #{variant_id} does not belong to product #{product_id}",
                )

            images.update(
                image_id,
                url=data["url"],
                alt=data.get("alt"),
                variant_id=variant_id,
                position=data.get("position") or 0,
            )
            return images.get(image_id), 200

    @ns.marshal_with(image_model)
    @ns.response(200, "The deleted image")
    @ns.response(404, "Image does not belong to this product")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, product_id, image_id):
        """Remove an image from a product."""
        with get_db_connection() as (_, cursor):
            images = ProductImageRepository(cursor)

            if not images.belongs_to(image_id, product_id):
                ns.abort(
                    404,
                    f"Image #{image_id} does not belong to product #{product_id}",
                )

            image = images.get(image_id)
            images.delete(image_id)
            # Only removes the file if it was one we stored, so seeded assets
            # and hand-written paths survive.
            uploads.delete(image["url"])
            return image, 200
