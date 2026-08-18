"""Collections: themed groupings such as "Barra da Saia".

A collection owns colour sets, and products may belong to one. Deleting a
collection leaves its colour sets and products in place, simply unowned.
"""

from flask_restx import Namespace, Resource

from db import get_db_connection
from api.models.catalog import (
    collection_list_model,
    collection_model,
    collection_write_model,
)
from api.models.common import pagination_model
from repositories import CollectionRepository
from api.routes.crud import get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, auth_required

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
        with get_db_connection() as (_, cursor):
            return page_of(CollectionRepository(cursor), "collections")

    @ns.expect(collection_write_model, validate=True)
    @ns.marshal_with(collection_model, code=201)
    @ns.response(201, "Collection created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A collection with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a new collection."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            reject_duplicate_name(ns, collections, data["name"], "Collection")

            collection_id = collections.create(
                name=data["name"], description=data.get("description")
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
            return get_or_404(
                ns, CollectionRepository(cursor), collection_id, "Collection"
            )

    @ns.expect(collection_write_model, validate=True)
    @ns.marshal_with(collection_model)
    @ns.response(200, "Collection updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Collection not found")
    @ns.response(409, "Another collection already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, collection_id):
        """Update a collection by ID."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            get_or_404(ns, collections, collection_id, "Collection")
            reject_duplicate_name(
                ns, collections, data["name"], "Collection", exclude_id=collection_id
            )

            collections.update(
                collection_id,
                name=data["name"],
                description=data.get("description"),
            )
            return collections.get(collection_id), 200

    @ns.marshal_with(collection_model)
    @ns.response(200, "The deleted collection")
    @ns.response(404, "Collection not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, collection_id):
        """Delete a collection by ID.

        Its colour sets and products stay, detached from any collection.
        """
        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            collection = get_or_404(ns, collections, collection_id, "Collection")

            collections.delete(collection_id)
            return collection, 200
