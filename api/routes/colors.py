"""Colours: the individual swatches that colour sets are built from."""

from flask_restx import Namespace, Resource

from db import get_db_connection
from api.models.catalog import color_list_model, color_model, color_write_model
from api.models.common import pagination_model
from repositories import ColorRepository
from api.routes.crud import CREATED, get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, auth_required

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
        with get_db_connection() as (_, cursor):
            return page_of(ColorRepository(cursor), "colors")

    @ns.expect(color_write_model, validate=True)
    @ns.marshal_with(color_model, code=CREATED)
    @ns.response(201, "Colour created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A colour with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a new colour."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)
            reject_duplicate_name(ns, colors, data["name"], "Colour")

            color_id = colors.create(name=data["name"], hex=data.get("hex"))
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
            return get_or_404(ns, ColorRepository(cursor), color_id, "Colour")

    @ns.expect(color_write_model, validate=True)
    @ns.marshal_with(color_model)
    @ns.response(200, "Colour updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Colour not found")
    @ns.response(409, "Another colour already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, color_id):
        """Update a colour by ID."""
        data = ns.payload

        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)
            get_or_404(ns, colors, color_id, "Colour")
            reject_duplicate_name(
                ns, colors, data["name"], "Colour", exclude_id=color_id
            )

            colors.update(color_id, name=data["name"], hex=data.get("hex"))
            return colors.get(color_id), 200

    @ns.marshal_with(color_model)
    @ns.response(200, "The deleted colour")
    @ns.response(404, "Colour not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, color_id):
        """Delete a colour by ID.

        Any colour set that used it loses it from its swatch list.
        """
        with get_db_connection() as (_, cursor):
            colors = ColorRepository(cursor)
            color = get_or_404(ns, colors, color_id, "Colour")

            colors.delete(color_id)
            return color, 200
