"""Colours: the individual swatches that colour sets are built from."""

from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.catalog import color_list_model, color_model, color_write_model
from api.models.common import pagination_model
from api.pagination import get_pagination_params, make_pagination
from api.security import PROTECTED_DOC, token_required
from api.repositories import ColorRepository

ns = Namespace("colors", description="Colours operations")

for model in [pagination_model, color_model, color_list_model, color_write_model]:
    ns.models[model.name] = model


@ns.route("/")
class ColorList(Resource):
    @ns.marshal_with(color_list_model)
    @ns.param("q", "Search term for colour name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of colours")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List colours with pagination and optional fuzzy search."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")

        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)

            return {
                "colors": colors.list(search=search, limit=limit, offset=offset),
                "pagination": make_pagination(colors.count(search=search), page, limit),
            }

    @ns.expect(color_write_model, validate=True)
    @ns.marshal_with(color_model, code=201)
    @ns.response(201, "Colour created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A colour with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @token_required
    def post(self):
        """Create a new colour."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)

            if colors.name_exists(name):
                ns.abort(409, f"The colour '{name}' already exists.")

            color_id = colors.create(name=name, hex=data.get("hex"))
            return colors.get(color_id), 201


@ns.route("/<int:color_id>")
@ns.param("color_id", "The colour identifier")
class Color(Resource):
    @ns.marshal_with(color_model)
    @ns.response(200, "The colour")
    @ns.response(404, "Colour not found")
    def get(self, color_id):
        """Get a colour by ID."""
        with get_db_connection() as (_, cursor):
            color = ColorRepository(cursor).get(color_id)
            if not color:
                ns.abort(404, f"Colour #{color_id} not found")

            return color

    @ns.expect(color_write_model, validate=True)
    @ns.marshal_with(color_model)
    @ns.response(200, "Colour updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Colour not found")
    @ns.response(409, "Another colour already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @token_required
    def put(self, color_id):
        """Update a colour by ID."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)

            if not colors.exists(color_id):
                ns.abort(404, f"Colour #{color_id} not found")

            if colors.name_exists(name, exclude_id=color_id):
                ns.abort(
                    409, f"Colour name '{name}' is already used by another colour."
                )

            colors.update(color_id, name=name, hex=data.get("hex"))
            return colors.get(color_id), 200

    @ns.marshal_with(color_model)
    @ns.response(200, "The deleted colour")
    @ns.response(404, "Colour not found")
    @ns.doc(**PROTECTED_DOC)
    @token_required
    def delete(self, color_id):
        """Delete a colour by ID.

        The colour is also removed from any colour set that contained it.
        """
        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)

            color = colors.get(color_id)
            if not color:
                ns.abort(404, f"Colour #{color_id} not found")

            colors.delete(color_id)
            return color, 200
