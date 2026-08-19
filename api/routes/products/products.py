"""The product collection and one product: list, create, read, update, delete."""

from flask import request

import uploads
from db import get_db_connection
from api.models.products import (
    facet_counts_model,
    product_create_model,
    product_list_model,
    product_model,
    update_product_model,
)
from api.pagination import get_pagination_params, make_pagination
from api.routes.products import ns
from api.security import PROTECTED_DOC, auth_required
from repositories import (
    CollectionRepository,
    MaterialRepository,
    ProductRepository,
    ProductTypeRepository,
    SizeRepository,
)
from flask_restx import Resource


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
    @ns.param(
        "material_id",
        "Only products made of this material. Repeatable — several values read "
        "as OR, while a different filter still narrows with AND.",
    )
    @ns.param("collection_id", "Only products in this collection. Repeatable.")
    @ns.param("type_id", "Only products of this type. Repeatable.")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.param(
        "photographed_first",
        "Return pieces that have photographs before those that do not, as the "
        "storefront does. Off by default, which is insertion order.",
    )
    @ns.response(200, "A page of products")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List products with pagination, fuzzy search and filters."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")
        # getlist, so ?type_id=1&type_id=5 asks for both families. A single value
        # arrives as a one-item list, which is what the old callers send.
        material_id = request.args.getlist("material_id", type=int)
        collection_id = request.args.getlist("collection_id", type=int)
        type_id = request.args.getlist("type_id", type=int)
        photographed_first = bool(request.args.get("photographed_first", type=int))

        with get_db_connection() as (_, cursor):
            products = ProductRepository(cursor)
            filters = {
                "search": search,
                "material_id": material_id,
                "collection_id": collection_id,
                "type_id": type_id,
            }

            return {
                "products": products.list(
                    **filters,
                    limit=limit,
                    offset=offset,
                    photographed_first=photographed_first,
                ),
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


@ns.route("/facets")
class ProductFacets(Resource):
    @ns.marshal_with(facet_counts_model)
    @ns.response(200, "How many products sit behind each filter option")
    def get(self):
        """Per-option product counts, for the catalogue's filter sidebar.

        One request rather than a count on each of the three lookup endpoints,
        because the answer is about products, not about types or materials.
        """
        with get_db_connection() as (_, cursor):
            return ProductRepository(cursor).facet_counts()


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

            # Its photographs' files go with their rows, product-level and
            # per-colour alike; anything it merely pointed at is left alone.
            uploads.delete_many(products.delete(product_id))
            return product, 200
