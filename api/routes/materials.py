"""Materials: what a piece is made of.

A lookup the owners maintain themselves, and optional on a product — a piece that
mixes materials, or one nobody has classified yet, simply has none. Deleting a
material therefore detaches the pieces made of it rather than deleting them.
"""

from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.common import pagination_model
from api.models.materials import (
    material_list_model,
    material_model,
    material_write_model,
)
from api.repositories import MaterialRepository
from api.routes.crud import get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, auth_required

ns = Namespace("materials", description="Materials operations")

for model in [
    pagination_model,
    material_model,
    material_list_model,
    material_write_model,
]:
    ns.models[model.name] = model


@ns.route("/")
class MaterialList(Resource):
    @ns.marshal_with(material_list_model)
    @ns.param("q", "Search term for material name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of materials")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List materials with pagination and optional fuzzy search."""
        with get_db_connection() as (_, cursor):
            return page_of(MaterialRepository(cursor), "materials")

    @ns.expect(material_write_model, validate=True)
    @ns.marshal_with(material_model, code=201)
    @ns.response(201, "Material created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A material with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def post(self):
        """Create a new material."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            materials = MaterialRepository(cursor)
            reject_duplicate_name(ns, materials, name, "Material")

            material_id = materials.create(name)
            return materials.get(material_id), 201


@ns.route("/<int:material_id>")
@ns.param("material_id", "The material identifier")
class Material(Resource):
    @ns.marshal_with(material_model)
    @ns.response(200, "The material")
    @ns.response(404, "Material not found")
    def get(self, material_id):
        """Get a material by ID."""
        with get_db_connection() as (_, cursor):
            return get_or_404(ns, MaterialRepository(cursor), material_id, "Material")

    @ns.expect(material_write_model, validate=True)
    @ns.marshal_with(material_model)
    @ns.response(200, "Material updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Material not found")
    @ns.response(409, "Another material already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def put(self, material_id):
        """Update a material by ID."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            materials = MaterialRepository(cursor)
            get_or_404(ns, materials, material_id, "Material")
            reject_duplicate_name(
                ns, materials, name, "Material", exclude_id=material_id
            )

            materials.update(material_id, name)
            return materials.get(material_id), 200

    @ns.marshal_with(material_model)
    @ns.response(200, "The deleted material")
    @ns.response(404, "Material not found")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def delete(self, material_id):
        """Delete a material by ID.

        The pieces made of it keep existing, with no material set.
        """
        with get_db_connection() as (_, cursor):
            materials = MaterialRepository(cursor)
            material = get_or_404(ns, materials, material_id, "Material")

            materials.delete(material_id)
            return material, 200
