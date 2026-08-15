"""Colour sets: named colour combinations that products are offered in.

A colour set such as "White and Green" normally belongs to a collection, and a
product references it through a variant. One "caixa redonda" offered in
white/green, red/white, blue/white and white/gray is one product with four
variants pointing at four colour sets.
"""

from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.catalog import (
    collection_ref_model,
    color_model,
    color_set_list_model,
    color_set_model,
    color_set_write_model,
)
from api.models.common import pagination_model
from api.pagination import get_pagination_params, make_pagination
from api.repositories import ColorRepository, ColorSetRepository, CollectionRepository

ns = Namespace("color-sets", description="Colour set operations")

for model in [
    pagination_model,
    collection_ref_model,
    color_model,
    color_set_model,
    color_set_list_model,
    color_set_write_model,
]:
    ns.models[model.name] = model


def _validate_refs(cursor, *, collection_id, color_ids):
    """Reject unknown collections or colours before writing."""
    if collection_id is not None and not CollectionRepository(cursor).exists(
        collection_id
    ):
        ns.abort(404, f"The collection #{collection_id} does not exist.")

    missing = ColorRepository(cursor).missing_ids(color_ids)
    if missing:
        ns.abort(404, f"Unknown colour IDs: {sorted(missing)}")


@ns.route("/")
class ColorSetList(Resource):
    @ns.marshal_with(color_set_list_model)
    @ns.param("q", "Search term for colour set name (fuzzy search)")
    @ns.param("collection_id", "Only sets belonging to this collection")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of colour sets")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List colour sets with pagination, search and collection filter."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")
        collection_id = request.args.get("collection_id", type=int)

        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)

            return {
                "color_sets": color_sets.list(
                    search=search,
                    collection_id=collection_id,
                    limit=limit,
                    offset=offset,
                ),
                "pagination": make_pagination(
                    color_sets.count(search=search, collection_id=collection_id),
                    page,
                    limit,
                ),
            }

    @ns.expect(color_set_write_model, validate=True)
    @ns.marshal_with(color_set_model, code=201)
    @ns.response(201, "Colour set created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Referenced collection or colour does not exist")
    @ns.response(409, "That collection already has a set with this name")
    def post(self):
        """Create a colour set from a list of colours."""
        data = ns.payload
        name = data["name"]
        collection_id = data.get("collection_id")
        color_ids = data["color_ids"]

        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)
            _validate_refs(cursor, collection_id=collection_id, color_ids=color_ids)

            if color_sets.name_exists(name, collection_id=collection_id):
                ns.abort(409, f"The colour set '{name}' already exists here.")

            color_set_id = color_sets.create(
                name=name, collection_id=collection_id, color_ids=color_ids
            )
            return color_sets.get(color_set_id), 201


@ns.route("/<int:color_set_id>")
@ns.param("color_set_id", "The colour set identifier")
class ColorSet(Resource):
    @ns.marshal_with(color_set_model)
    @ns.response(200, "The colour set")
    @ns.response(404, "Colour set not found")
    def get(self, color_set_id):
        """Get a colour set by ID."""
        with get_db_connection() as (_, cursor):
            color_set = ColorSetRepository(cursor).get(color_set_id)
            if not color_set:
                ns.abort(404, f"Colour set #{color_set_id} not found")

            return color_set

    @ns.expect(color_set_write_model, validate=True)
    @ns.marshal_with(color_set_model)
    @ns.response(200, "Colour set updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Colour set, collection or colour not found")
    @ns.response(409, "That collection already has a set with this name")
    def put(self, color_set_id):
        """Update a colour set, replacing its colours wholesale."""
        data = ns.payload
        name = data["name"]
        collection_id = data.get("collection_id")
        color_ids = data["color_ids"]

        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)

            if not color_sets.exists(color_set_id):
                ns.abort(404, f"Colour set #{color_set_id} not found")

            _validate_refs(cursor, collection_id=collection_id, color_ids=color_ids)

            if color_sets.name_exists(
                name, collection_id=collection_id, exclude_id=color_set_id
            ):
                ns.abort(409, f"The colour set '{name}' already exists here.")

            color_sets.update(
                color_set_id,
                name=name,
                collection_id=collection_id,
                color_ids=color_ids,
            )
            return color_sets.get(color_set_id), 200

    @ns.marshal_with(color_set_model)
    @ns.response(200, "The deleted colour set")
    @ns.response(404, "Colour set not found")
    def delete(self, color_set_id):
        """Delete a colour set by ID.

        Any product variant offered in this colour set is removed with it.
        """
        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)

            color_set = color_sets.get(color_set_id)
            if not color_set:
                ns.abort(404, f"Colour set #{color_set_id} not found")

            color_sets.delete(color_set_id)
            return color_set, 200
