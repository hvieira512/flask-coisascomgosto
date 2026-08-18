"""Product types: the family a piece belongs to.

A type is broad — a box, a heart, a picture frame, a Christmas ornament. What
shape it is and how it is finished live in the product's own name, so "Caixa" is
the type and "Caixa rectangular" and "Caixa de Joias" are two products of it.
The list is flat: there is no level between the family and the piece.
"""

from flask_restx import Namespace, Resource

from db import get_db_connection
from api.models.catalog import (
    product_type_list_model,
    product_type_model,
    product_type_write_model,
)
from api.models.common import pagination_model
from api.routes.crud import page_of
from api.security import PROTECTED_DOC, auth_required
from repositories import ProductTypeRepository

ns = Namespace("product-types", description="Product type operations")

for model in [
    pagination_model,
    product_type_model,
    product_type_list_model,
    product_type_write_model,
]:
    ns.models[model.name] = model


@ns.route("/")
class ProductTypeList(Resource):
    @ns.marshal_with(product_type_list_model)
    @ns.param("q", "Search term for type name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of product types")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List product types with pagination and search."""
        with get_db_connection() as (_, cursor):
            return page_of(ProductTypeRepository(cursor), "product_types")

    @ns.expect(product_type_write_model, validate=True)
    @ns.marshal_with(product_type_model, code=201)
    @ns.response(201, "Product type created")
    @ns.response(400, "Missing fields")
    @ns.response(409, "A type already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a product type."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            types = ProductTypeRepository(cursor)

            if types.name_exists(name):
                ns.abort(409, f"The product type '{name}' already exists.")

            type_id = types.create(
                name=name,
                description=data.get("description"),
                icon=data.get("icon"),
            )
            return types.get(type_id), 201


@ns.route("/<int:type_id>")
@ns.param("type_id", "The product type identifier")
class ProductType(Resource):
    @ns.marshal_with(product_type_model)
    @ns.response(200, "The product type")
    @ns.response(404, "Product type not found")
    def get(self, type_id):
        """Get a product type by ID."""
        with get_db_connection() as (_, cursor):
            product_type = ProductTypeRepository(cursor).get(type_id)
            if not product_type:
                ns.abort(404, f"Product type #{type_id} not found")

            return product_type

    @ns.expect(product_type_write_model, validate=True)
    @ns.marshal_with(product_type_model)
    @ns.response(200, "Product type updated")
    @ns.response(404, "Product type not found")
    @ns.response(409, "Another type already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, type_id):
        """Update a product type."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            types = ProductTypeRepository(cursor)

            if not types.exists(type_id):
                ns.abort(404, f"Product type #{type_id} not found")

            if types.name_exists(name, exclude_id=type_id):
                ns.abort(409, f"The product type '{name}' already exists.")

            types.update(
                type_id,
                name=name,
                description=data.get("description"),
                icon=data.get("icon"),
            )
            return types.get(type_id), 200

    @ns.marshal_with(product_type_model)
    @ns.response(200, "The deleted product type")
    @ns.response(404, "Product type not found")
    @ns.response(409, "The type is still in use by at least one product")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, type_id):
        """Delete a product type by ID.

        A type still in use cannot be deleted: every piece must have one, so
        there is nowhere for those pieces to land. Move them first.
        """
        with get_db_connection() as (_, cursor):
            types = ProductTypeRepository(cursor)

            product_type = types.get(type_id)
            if not product_type:
                ns.abort(404, f"Product type #{type_id} not found")

            in_use = types.product_count(type_id)
            if in_use:
                ns.abort(
                    409,
                    f"{in_use} "
                    + ("product still uses" if in_use == 1 else "products still use")
                    + " this type. Move them to another type first.",
                )

            types.delete(type_id)
            return product_type, 200
