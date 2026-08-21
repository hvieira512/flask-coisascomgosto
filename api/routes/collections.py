"""Collections: themed groupings such as "Barra da Saia".

A collection owns colour sets, and products may belong to one. Deleting a
collection leaves its colour sets and products in place, simply unowned.
"""

from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage

import uploads
from db import get_db_connection
from api.models.catalog import (
    collection_color_sets_write_model,
    collection_list_model,
    collection_model,
    collection_ref_model,
    collection_write_model,
    color_model,
    color_set_model,
)
from api.models.common import pagination_model
from repositories import CollectionRepository, ColorSetRepository
from api.routes.crud import CREATED, bail, get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, auth_required

ns = Namespace("collections", description="Collections operations")

for model in [
    pagination_model,
    collection_model,
    collection_list_model,
    collection_write_model,
    collection_color_sets_write_model,
    # color_set_model nests both of these, and Swagger needs them registered here
    # too or the schema for this namespace has dangling references.
    collection_ref_model,
    color_model,
    color_set_model,
]:
    ns.models[model.name] = model

cover_parser = ns.parser()
cover_parser.add_argument(
    "file", location="files", type=FileStorage, required=True,
    help="Cover photograph: jpg, png or webp, up to 5 MB",
)


def _replace_cover(collections, collection, image_url):
    """Point a collection at a new cover.

    The file it replaces is left alone. It stops being referenced, so the sweep
    removes it later — which also means a cover pointed at one of the pieces' own
    photographs cannot take that photograph with it, since the product row still
    references the file.
    """
    collections.update(
        collection["id"],
        name=collection["name"],
        description=collection.get("description"),
        image_url=image_url,
    )


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
    @ns.marshal_with(collection_model, code=CREATED)
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
                name=data["name"],
                description=data.get("description"),
                image_url=data.get("image_url"),
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
                image_url=data.get("image_url"),
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
            # The cover file stays. Nothing references it once the row is gone, so
            # the sweep collects it later — and a cover pointed at one of the
            # pieces' own photographs cannot take that photograph with it.
            return collection, 200


@ns.route("/<int:collection_id>/color-sets")
@ns.param("collection_id", "The collection identifier")
class CollectionColorSets(Resource):
    @ns.marshal_list_with(color_set_model)
    @ns.response(200, "The colour sets belonging to this collection")
    @ns.response(404, "Collection not found")
    def get(self, collection_id):
        """List the colour sets belonging to this collection."""
        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            get_or_404(ns, collections, collection_id, "Collection")

            return ColorSetRepository(cursor).list(
                collection_id=collection_id, limit=100, offset=0
            )

    @ns.expect(collection_color_sets_write_model, validate=True)
    @ns.marshal_list_with(color_set_model)
    @ns.response(200, "The collection's colour sets after the replacement")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Collection or colour set not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, collection_id):
        """Replace the set of colour sets belonging to this collection.

        A colour set belongs to at most one collection, so this moves rather than
        links: one listed here leaves the collection it was in, and one that was here
        and is no longer listed ends up belonging to none. Send an empty list to
        empty the collection.
        """
        color_set_ids = ns.payload["color_set_ids"]

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            get_or_404(ns, collections, collection_id, "Collection")

            color_sets = ColorSetRepository(cursor)
            missing = [
                set_id for set_id in color_set_ids if not color_sets.exists(set_id)
            ]
            if missing:
                ns.abort(404, f"Unknown colour set IDs: {sorted(missing)}")

            color_sets.set_collection(collection_id, color_set_ids)
            return color_sets.list(collection_id=collection_id, limit=100, offset=0)


@ns.route("/<int:collection_id>/cover")
@ns.param("collection_id", "The collection identifier")
class CollectionCover(Resource):
    @ns.expect(cover_parser)
    @ns.marshal_with(collection_model, code=CREATED)
    @ns.response(201, "Cover stored and attached")
    @ns.response(400, "Missing file, unsupported format, or too large")
    @ns.response(404, "Collection not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self, collection_id):
        """Upload the photograph that stands for this collection."""
        args = cover_parser.parse_args()

        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            collection = get_or_404(ns, collections, collection_id, "Collection")

            try:
                url = uploads.save(
                    args["file"],
                    folder=uploads.COLLECTION_DIR,
                    url_prefix=uploads.COLLECTION_PREFIX,
                )
            except uploads.UploadError as error:
                bail(ns, 400, str(error))

            _replace_cover(collections, collection, url)
            return collections.get(collection_id), 201

    @ns.marshal_with(collection_model)
    @ns.response(200, "The collection, with no cover")
    @ns.response(404, "Collection not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, collection_id):
        """Remove this collection's cover photograph."""
        with get_db_connection() as (_, cursor):
            collections = CollectionRepository(cursor)
            collection = get_or_404(ns, collections, collection_id, "Collection")

            _replace_cover(collections, collection, None)
            return collections.get(collection_id), 200
