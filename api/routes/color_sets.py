"""Colour sets: named colour combinations that products are offered in.

A colour set such as "Preto e Branco" is two or more colours named once and
shared, and a product references it through a variant. One "Caixa Redonda"
offered in four combinations is one product with four variants pointing at four
colour sets.

A set may appear in several collections or in none — the same two colours are the
same combination whichever collection shows them — so `collection_ids` is a list
and the name is unique across the whole catalogue.
"""

from flask import request
from flask_restx import Namespace, Resource

import uploads
from db import get_db_connection
from api.models.catalog import (
    collection_ref_model,
    color_model,
    color_set_list_model,
    color_set_model,
    color_set_write_model,
)
from api.models.common import pagination_model
from repositories import ColorRepository, ColorSetRepository, CollectionRepository
from api.routes.crud import CREATED, page_of
from api.security import PROTECTED_DOC, auth_required

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


def _validate_refs(cursor, *, collection_ids, color_ids):
    """Reject unknown collections or colours before writing."""
    collections = CollectionRepository(cursor)
    for collection_id in collection_ids or []:
        if not collections.exists(collection_id):
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
        with get_db_connection() as (_, cursor):
            return page_of(
                ColorSetRepository(cursor),
                "color_sets",
                collection_id=request.args.get("collection_id", type=int),
            )

    @ns.expect(color_set_write_model, validate=True)
    @ns.marshal_with(color_set_model, code=CREATED)
    @ns.response(201, "Colour set created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Referenced collection or colour does not exist")
    @ns.response(409, "A colour set with this name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a colour set from a list of colours."""
        data = ns.payload
        name = data["name"]
        collection_ids = data.get("collection_ids") or []
        color_ids = data["color_ids"]

        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)
            _validate_refs(cursor, collection_ids=collection_ids, color_ids=color_ids)

            if color_sets.name_exists(name):
                ns.abort(409, f"The colour set '{name}' already exists.")

            color_set_id = color_sets.create(
                name=name, color_ids=color_ids, collection_ids=collection_ids
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
    @ns.response(409, "A colour set with this name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, color_set_id):
        """Update a colour set, replacing its colours and collections wholesale."""
        data = ns.payload
        name = data["name"]
        collection_ids = data.get("collection_ids") or []
        color_ids = data["color_ids"]

        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)

            if not color_sets.exists(color_set_id):
                ns.abort(404, f"Colour set #{color_set_id} not found")

            _validate_refs(cursor, collection_ids=collection_ids, color_ids=color_ids)

            if color_sets.name_exists(name, exclude_id=color_set_id):
                ns.abort(409, f"The colour set '{name}' already exists.")

            color_sets.update(
                color_set_id,
                name=name,
                color_ids=color_ids,
                collection_ids=collection_ids,
            )
            return color_sets.get(color_set_id), 200

    @ns.marshal_with(color_set_model)
    @ns.response(200, "The deleted colour set")
    @ns.response(404, "Colour set not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, color_set_id):
        """Delete a colour set by ID.

        Any product variant offered in this colour set is removed with it.
        """
        with get_db_connection() as (_, cursor):
            color_sets = ColorSetRepository(cursor)

            color_set = color_sets.get(color_set_id)
            if not color_set:
                ns.abort(404, f"Colour set #{color_set_id} not found")

            # Deleting a set removes every variant offered in it, and their
            # photographs' rows with them. The files stay until the sweep.
            color_sets.delete(color_set_id)
            return color_set, 200
