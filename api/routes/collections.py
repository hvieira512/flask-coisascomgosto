"""Collections: themed groupings such as "Barra da Saia".

A collection owns colour sets, and products may belong to one. Deleting a
collection leaves its colour sets and products in place, simply unowned.
"""

from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.catalog import (
    collection_list_model,
    collection_model,
    collection_write_model,
)
from api.models.common import pagination_model
from api.pagination import get_pagination_params, make_pagination
from api.repositories import CollectionRepository

ns = Namespace("collections", description="Collections operations")

for model in [
    pagination_model,
    collection_model,
    collection_list_model,
    collection_write_model,
]:
    ns.models[model.name] = model


@ns.route("/")
class CollectionList(Resource):
    @ns.marshal_with(collection_list_model)
    @ns.param("q", "Search term for collection name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of collections")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List collections with pagination and optional fuzzy search."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)

            return {
                "collections": collections.list(
                    search=search, limit=limit, offset=offset
                ),
                "pagination": make_pagination(
                    collections.count(search=search), page, limit
                ),
            }

    @ns.expect(collection_write_model, validate=True)
    @ns.marshal_with(collection_model, code=201)
    @ns.response(201, "Collection created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A collection with that name already exists")
    def post(self):
        """Create a new collection."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)

            if collections.name_exists(name):
                ns.abort(409, f"The collection '{name}' already exists.")

            collection_id = collections.create(
                name=name, description=data.get("description")
            )
            return collections.get(collection_id), 201


@ns.route("/<int:collection_id>")
@ns.param("collection_id", "The collection identifier")
class Collection(Resource):
    @ns.marshal_with(collection_model)
    @ns.response(200, "The collection")
    @ns.response(404, "Collection not found")
    def get(self, collection_id):
        """Get a collection by ID."""
        with get_db_connection() as (_, cursor):
            collection = CollectionRepository(cursor).get(collection_id)
            if not collection:
                ns.abort(404, f"Collection #{collection_id} not found")

            return collection

    @ns.expect(collection_write_model, validate=True)
    @ns.marshal_with(collection_model)
    @ns.response(200, "Collection updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Collection not found")
    @ns.response(409, "Another collection already uses that name")
    def put(self, collection_id):
        """Update a collection by ID."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)

            if not collections.exists(collection_id):
                ns.abort(404, f"Collection #{collection_id} not found")

            if collections.name_exists(name, exclude_id=collection_id):
                ns.abort(
                    409,
                    f"Collection name '{name}' is already used by another collection.",
                )

            collections.update(
                collection_id, name=name, description=data.get("description")
            )
            return collections.get(collection_id), 200

    @ns.marshal_with(collection_model)
    @ns.response(200, "The deleted collection")
    @ns.response(404, "Collection not found")
    def delete(self, collection_id):
        """Delete a collection by ID.

        Its colour sets and products survive with their collection cleared.
        """
        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)

            collection = collections.get(collection_id)
            if not collection:
                ns.abort(404, f"Collection #{collection_id} not found")

            collections.delete(collection_id)
            return collection, 200
