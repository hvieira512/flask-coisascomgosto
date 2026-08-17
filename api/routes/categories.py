"""Categories: the one grouping every product must have."""

from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.categories import (
    category_create_model,
    category_list_model,
    category_model,
)
from api.models.common import pagination_model
from api.repositories import CategoryRepository
from api.routes.crud import get_or_404, page_of, reject_duplicate_name
from api.security import PROTECTED_DOC, login_required

ns = Namespace("categories", description="Categories operations")

for model in [
    pagination_model,
    category_model,
    category_list_model,
    category_create_model,
]:
    ns.models[model.name] = model


@ns.route("/")
class CategoryList(Resource):
    @ns.marshal_with(category_list_model)
    @ns.param("q", "Search term for category name (fuzzy search)")
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of categories")
    @ns.response(400, "Invalid pagination parameters")
    def get(self):
        """List categories with pagination and optional fuzzy search."""
        with get_db_connection() as (_, cursor):
            return page_of(CategoryRepository(cursor), "categories")

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model, code=201)
    @ns.response(201, "Category created")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(409, "A category with that name already exists")
    @ns.doc(**PROTECTED_DOC)
    @login_required
    def post(self):
        """Create a new category."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)
            reject_duplicate_name(ns, categories, name, "Category")

            category_id = categories.create(name)
            return categories.get(category_id), 201


@ns.route("/<int:category_id>")
@ns.param("category_id", "The category identifier")
class Category(Resource):
    @ns.marshal_with(category_model)
    @ns.response(200, "The category")
    @ns.response(404, "Category not found")
    def get(self, category_id):
        """Get a category by ID."""
        with get_db_connection() as (_, cursor):
            return get_or_404(ns, CategoryRepository(cursor), category_id, "Category")

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model)
    @ns.response(200, "Category updated")
    @ns.response(400, "Missing or invalid fields")
    @ns.response(404, "Category not found")
    @ns.response(409, "Another category already uses that name")
    @ns.doc(**PROTECTED_DOC)
    @login_required
    def put(self, category_id):
        """Update a category by ID."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)
            get_or_404(ns, categories, category_id, "Category")
            reject_duplicate_name(
                ns, categories, name, "Category", exclude_id=category_id
            )

            categories.update(category_id, name)
            return categories.get(category_id), 200

    @ns.marshal_with(category_model)
    @ns.response(200, "The deleted category")
    @ns.response(404, "Category not found")
    @ns.doc(**PROTECTED_DOC)
    @login_required
    def delete(self, category_id):
        """Delete a category by ID.

        Every product filed under it is deleted too, along with that product's
        own images, sizes and variants.
        """
        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)
            category = get_or_404(ns, categories, category_id, "Category")

            categories.delete(category_id)
            return category, 200
