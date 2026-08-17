"""Sizes: the S / M / L vocabulary products can be sold in.

The schema seeds S, M and L. A product may name one size as its default and
list the sizes it is actually available in; a product with no listed sizes is
sold only in its default size.
"""

from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.catalog import size_list_model, size_model, size_write_model
from api.models.common import pagination_model
from api.repositories import SizeRepository
from api.routes.crud import get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, auth_required

ns = Namespace("sizes", description="Sizes operations")

for model in [pagination_model, size_model, size_list_model, size_write_model]:
    ns.models[model.name] = model


@ns.route("/")
class SizeList(Resource):
    @ns.marshal_with(size_list_model)
    @ns.param("q", "Search term for size name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of sizes, ordered by display position")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List sizes with pagination and optional fuzzy search."""
        with get_db_connection() as (_, cursor):
            return page_of(SizeRepository(cursor), "sizes")

    @ns.expect(size_write_model, validate=True)
    @ns.marshal_with(size_model, code=201)
    @ns.response(201, "Size created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A size with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a new size."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            sizes = SizeRepository(cursor)
            reject_duplicate_name(ns, sizes, data["name"], "Size")

            size_id = sizes.create(
                name=data["name"], position=data.get("position") or 0
            )
            return sizes.get(size_id), 201


@ns.route("/<int:size_id>")
@ns.param("size_id", "The size identifier")
class Size(Resource):
    @ns.marshal_with(size_model)
    @ns.response(200, "The size")
    @ns.response(404, "Size not found")
    def get(self, size_id):
        """Get a size by ID."""
        with get_db_connection() as (_, cursor):
            return get_or_404(ns, SizeRepository(cursor), size_id, "Size")

    @ns.expect(size_write_model, validate=True)
    @ns.marshal_with(size_model)
    @ns.response(200, "Size updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Size not found")
    @ns.response(409, "Another size already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, size_id):
        """Update a size by ID."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            sizes = SizeRepository(cursor)
            get_or_404(ns, sizes, size_id, "Size")
            reject_duplicate_name(ns, sizes, data["name"], "Size", exclude_id=size_id)

            sizes.update(
                size_id, name=data["name"], position=data.get("position") or 0
            )
            return sizes.get(size_id), 200

    @ns.marshal_with(size_model)
    @ns.response(200, "The deleted size")
    @ns.response(404, "Size not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, size_id):
        """Delete a size by ID.

        Products listing this size lose it, and any product using it as its
        default size falls back to having no default.
        """
        with get_db_connection() as (_, cursor):
            sizes = SizeRepository(cursor)
            size = get_or_404(ns, sizes, size_id, "Size")

            sizes.delete(size_id)
            return size, 200
