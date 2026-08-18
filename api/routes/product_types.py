"""Product types: what an object is, plus one level of sub-types.

Top-level types describe the object — a hairbrush, a picture frame, a wooden
box, a Coracao (a wooden plaque cut in the shape of the regional Viana heart).
Sub-types describe how that object is finished or used: the same Coracao may be
sold with a string so it can be hung, or as a base for mini figures displayed
on top.

Types nest exactly one level: a sub-type cannot itself have sub-types.
"""

from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.catalog import (
    product_type_list_model,
    product_type_model,
    product_type_ref_model,
    product_type_write_model,
)
from api.models.common import pagination_model
from api.routes.crud import page_of
from api.security import PROTECTED_DOC, auth_required
from api.repositories import NestingTooDeepError, ProductTypeRepository

ns = Namespace("product-types", description="Product type operations")

for model in [
    pagination_model,
    product_type_ref_model,
    product_type_model,
    product_type_list_model,
    product_type_write_model,
]:
    ns.models[model.name] = model


@ns.route("/")
class ProductTypeList(Resource):
    @ns.marshal_with(product_type_list_model)
    @ns.param("q", "Search term for type name (fuzzy search)")
    @ns.param("parent_id", "Only sub-types of this type")
    @ns.param("roots_only", "Set to 1 to return only top-level types")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of product types, each with its sub-types")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List product types with pagination, search and hierarchy filters."""
        with get_db_connection() as (_, cursor):
            return page_of(
                ProductTypeRepository(cursor),
                "product_types",
                parent_id=request.args.get("parent_id", type=int),
                roots_only=request.args.get("roots_only") in {"1", "true", "True"},
            )

    @ns.expect(product_type_write_model, validate=True)
    @ns.marshal_with(product_type_model, code=201)
    @ns.response(201, "Product type created")
    @ns.response(400, "Missing fields, or the parent is already a sub-type")
    @ns.response(404, "Parent type not found")
    @ns.response(409, "A sibling type already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a product type, or a sub-type by supplying parent_id."""
        data = ns.payload
        name = data["name"]
        parent_id = data.get("parent_id")

        with get_db_connection() as (_, cursor):
            types = ProductTypeRepository(cursor)

            if parent_id is not None and not types.exists(parent_id):
                ns.abort(404, f"The product type #{parent_id} does not exist.")

            if types.name_exists(name, parent_id=parent_id):
                ns.abort(409, f"The product type '{name}' already exists here.")

            try:
                type_id = types.create(
                    name=name,
                    parent_id=parent_id,
                    description=data.get("description"),
                    icon=data.get("icon"),
                )
            except NestingTooDeepError as exc:
                ns.abort(400, str(exc))

            return types.get(type_id), 201


@ns.route("/<int:type_id>")
@ns.param("type_id", "The product type identifier")
class ProductType(Resource):
    @ns.marshal_with(product_type_model)
    @ns.response(200, "The product type with its sub-types")
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
    @ns.response(400, "The move would nest types more than one level deep")
    @ns.response(404, "Product type or parent not found")
    @ns.response(409, "A sibling type already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, type_id):
        """Update a product type, including where it sits in the hierarchy."""
        data = ns.payload
        name = data["name"]
        parent_id = data.get("parent_id")

        with get_db_connection() as (_, cursor):
            types = ProductTypeRepository(cursor)

            if not types.exists(type_id):
                ns.abort(404, f"Product type #{type_id} not found")

            if parent_id is not None and not types.exists(parent_id):
                ns.abort(404, f"The product type #{parent_id} does not exist.")

            if types.name_exists(name, parent_id=parent_id, exclude_id=type_id):
                ns.abort(409, f"The product type '{name}' already exists here.")

            try:
                types.update(
                    type_id,
                    name=name,
                    parent_id=parent_id,
                    description=data.get("description"),
                    icon=data.get("icon"),
                )
            except NestingTooDeepError as exc:
                ns.abort(400, str(exc))

            return types.get(type_id), 200

    @ns.marshal_with(product_type_model)
    @ns.response(200, "The deleted product type")
    @ns.response(404, "Product type not found")
    @ns.response(409, "The type is still in use by at least one product")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, type_id):
        """Delete a product type by ID.

        Its sub-types go with it. A type still in use cannot be deleted: every
        piece must have one, so there is nowhere for those pieces to land. Move
        them to another type first.
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
