from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.categories import (
    category_create_model,
    category_list_model,
    category_model,
)
from api.models.common import pagination_model
from api.pagination import get_pagination_params, make_pagination
from api.repositories import CategoryRepository

ns = Namespace(
    "categories",
    description="Categories operations",
)

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
    def get(self):
        """Get list of categories with pagination and optional fuzzy search."""
        page, limit, offset = get_pagination_params(request.args)
        search = request.args.get("q")

        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)

            return {
                "categories": categories.list(
                    search=search, limit=limit, offset=offset
                ),
                "pagination": make_pagination(
                    categories.count(search=search), page, limit
                ),
            }

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model, code=201)
    def post(self):
        """Create a new category."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)

            if categories.name_exists(name):
                ns.abort(409, f"The category '{name}' already exists.")

            category_id = categories.create(name)
            return categories.get(category_id), 201


@ns.route("/<int:category_id>")
class Category(Resource):
    @ns.marshal_with(category_model)
    def get(self, category_id):
        """Get a category by ID."""
        with get_db_connection() as (_, cursor):
            category = CategoryRepository(cursor).get(category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            return category

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model)
    def put(self, category_id):
        """Update a category by ID."""
        name = ns.payload["name"]

        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)

            if not categories.exists(category_id):
                ns.abort(404, f"Category #{category_id} not found")

            if categories.name_exists(name, exclude_id=category_id):
                ns.abort(
                    409, f"Category name '{name}' is already used by another category."
                )

            categories.update(category_id, name)
            return categories.get(category_id), 200

    @ns.marshal_with(category_model)
    def delete(self, category_id):
        """Delete a category by ID."""
        with get_db_connection() as (_, cursor):
            categories = CategoryRepository(cursor)

            category = categories.get(category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            categories.delete(category_id)
            return category, 200
