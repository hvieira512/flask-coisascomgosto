"""Products, plus their variants and available sizes.

A product always has a product type (possibly a sub-type). It may also name
what it is made of, belong to a collection, declare a default size, list the sizes
it is available in, and carry one variant per colour set it is offered in.

Sub-resources:
    /products/<id>/variants        the colour sets this product is offered in
    /products/<id>/sizes           the sizes this product is available in
    /products/<id>/images          photographs, uploaded or referenced by path
"""

from flask import request
from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage

from api import uploads
from api.db import get_db_connection
from api.models.catalog import (
    collection_ref_model,
    color_model,
    color_set_model,
    image_model,
    image_write_model,
    product_sizes_write_model,
    product_type_nested_model,
    product_type_ref_model,
    size_model,
    variant_list_model,
    variant_model,
    variant_write_model,
)
from api.models.common import pagination_model
from api.models.products import (
    product_create_model,
    product_list_model,
    product_model,
    update_product_model,
)
from api.pagination import get_pagination_params, make_pagination
from api.security import PROTECTED_DOC, auth_required
from api.repositories import (
    MaterialRepository,
    CollectionRepository,
    ColorSetRepository,
    ProductImageRepository,
    ProductRepository,
    ProductTypeRepository,
    ProductVariantRepository,
    SizeRepository,
)

ns = Namespace("products", description="Products operations")

for model in [
    pagination_model,
    collection_ref_model,
    color_model,
    color_set_model,
    size_model,
    product_type_ref_model,
    product_type_nested_model,
    variant_model,
    variant_list_model,
    variant_write_model,
    image_model,
    image_write_model,
    product_sizes_write_model,
    product_model,
    product_list_model,
    product_create_model,
    update_product_model,
]:
    ns.models[model.name] = model


def _validate_refs(cursor, data):
    """Reject an unknown type, material, collection or default size before writing."""
    type_id = data["type_id"]
    if not ProductTypeRepository(cursor).exists(type_id):
        ns.abort(404, f"The product type #{type_id} does not exist.")

    if (material_id := data.get("material_id")) is not None and not MaterialRepository(
        cursor
    ).exists(material_id):
        ns.abort(404, f"The material #{material_id} does not exist.")

    if (
        collection_id := data.get("collection_id")
    ) is not None and not CollectionRepository(cursor).exists(collection_id):
        ns.abort(404, f"The collection #{collection_id} does not exist.")

    if (size_id := data.get("default_size_id")) is not None and not SizeRepository(
        cursor
    ).exists(size_id):
        ns.abort(404, f"The size #{size_id} does not exist.")


@ns.route("/")
class ProductList(Resource):
    @ns.marshal_with(product_list_model)
    @ns.param("q", "Search term for product or type name (fuzzy search)")
    @ns.param("material_id", "Only products made of this material")
    @ns.param("collection_id", "Only products in this collection")
    @ns.param(
        "type_id",
        "Only products of this type. Matching a top-level type also returns "
        "products filed under its sub-types.",
    )
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of products")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List products with pagination, fuzzy search and filters."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")
        material_id = request.args.get("material_id", type=int)
        collection_id = request.args.get("collection_id", type=int)
        type_id = request.args.get("type_id", type=int)

        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)
            filters = {
                "search": search,
                "material_id": material_id,
                "collection_id": collection_id,
                "type_id": type_id,
            }

            return {
                "products": products.list(**filters, limit=limit, offset=offset),
                "pagination": make_pagination(
                    products.count(**filters), page, limit
                ),
            }

    @ns.expect(product_create_model, validate=True)
    @ns.marshal_with(product_model, code=201)
    @ns.response(201, "Product created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Referenced type, material, collection or size not found")
    @ns.response(409, "A product with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a new product."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)
            _validate_refs(cursor, data)

            if products.name_exists(name):
                ns.abort(409, f"The product {name} already exists.")

            product_id = products.create(
                type_id=data["type_id"],
                material_id=data.get("material_id"),
                name=name,
                description=data["description"],
                collection_id=data.get("collection_id"),
                default_size_id=data.get("default_size_id"),
            )
            return products.get(product_id), 201


@ns.route("/<int:product_id>")
@ns.param("product_id", "The product identifier")
class Product(Resource):
    @ns.marshal_with(product_model)
    @ns.response(200, "The product")
    @ns.response(404, "Product not found")
    def get(self, product_id):
        """Get a product by ID, with its type, sizes and variants."""
        with get_db_connection() as (_, cursor):
            product = ProductRepository(cursor).get(product_id)
            if not product:
                ns.abort(404, f"Product #{product_id} not found")

            return product

    @ns.expect(update_product_model, validate=True)
    @ns.marshal_with(product_model)
    @ns.response(200, "Product updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Product, type, material, collection or size not found")
    @ns.response(409, "Another product already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, product_id):
        """Update a product's own fields.

        Variants and available sizes are managed through the sub-resources.
        """
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)

            if not products.exists(product_id):
                ns.abort(404, f"Product #{product_id} not found")

            _validate_refs(cursor, data)

            if products.name_exists(name, exclude_id=product_id):
                ns.abort(
                    409, f"Product name '{name}' is already used by another product"
                )

            products.update(
                product_id,
                type_id=data["type_id"],
                material_id=data.get("material_id"),
                name=name,
                description=data["description"],
                collection_id=data.get("collection_id"),
                default_size_id=data.get("default_size_id"),
            )
            return products.get(product_id), 200

    @ns.marshal_with(product_model)
    @ns.response(200, "The deleted product")
    @ns.response(404, "Product not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, product_id):
        """Delete a product by ID, along with its variants and size links."""
        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)

            product = products.get(product_id)
            if not product:
                ns.abort(404, f"Product #{product_id} not found")

            products.delete(product_id)
            return product, 200


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
    @ns.marshal_with(variant_model, code=201)
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
            variants.delete(variant_id)
            return variant, 200


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
