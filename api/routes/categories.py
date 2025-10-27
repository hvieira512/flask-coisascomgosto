from flask import request
from flask_restx import Namespace, Resource

from api.helpers.categories import (
    build_category_filters,
    category_exists_by_id,
    category_exists_by_name,
    category_name_taken,
    fetch_category_by_id,
)
from api.helpers.pagination import get_pagination_params, make_pagination
from api.models.categories import (
    category_create_model,
    category_list_model,
    category_model,
)
from api.models.common import pagination_model
from api.utils import get_db_connection

ns = Namespace(
    "categories",
    description="Categories operations",
)

ns.models[pagination_model.name] = pagination_model
ns.models[category_model.name] = category_model
ns.models[category_list_model.name] = category_list_model
ns.models[category_create_model.name] = category_create_model


@ns.route("/")
class CategoryList(Resource):
    @ns.marshal_with(category_list_model)
    @ns.param("q", "Search term for category name (fuzzy search)")
    def get(self):
        """Get list of categories with pagination and optional fuzzy search."""
        page, limit, offset = get_pagination_params(request.args)
        where_clause, params = build_category_filters(request.args)

        with get_db_connection() as (_, cursor):
            cursor.execute(f"SELECT COUNT(*) FROM categories {where_clause}", params)
            total = cursor.fetchone()[0]

            query = f"SELECT * FROM categories {where_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, params + [limit, offset])
            categories = [dict(row) for row in cursor.fetchall()]

            return {
                "categories": categories,
                "pagination": make_pagination(total, page, limit),
            }

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model, code=201)
    def post(self):
        """Create a new category."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (conn, cursor):
            if category_exists_by_name(cursor, name):
                ns.abort(409, f"The category '{name}' already exists.")

            cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            category_id = cursor.lastrowid
            conn.commit()

            category = fetch_category_by_id(cursor, category_id)
            return category, 201


@ns.route("/<int:category_id>")
class Category(Resource):
    @ns.marshal_with(category_model)
    def get(self, category_id):
        """Get a category by ID."""
        with get_db_connection() as (_, cursor):
            category = fetch_category_by_id(cursor, category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            return category

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model)
    def put(self, category_id):
        """Update a category by ID."""
        data = ns.payload
        name = data["name"]

        with get_db_connection() as (conn, cursor):
            if not category_exists_by_id(cursor, category_id):
                ns.abort(404, f"Category #{category_id} not found")

            if category_name_taken(cursor, name, category_id):
                ns.abort(
                    409, f"Category name '{name}' is already used by another category."
                )

            cursor.execute(
                "UPDATE categories SET name=? WHERE id=?", (name, category_id)
            )
            conn.commit()

            category = fetch_category_by_id(cursor, category_id)
            return category, 200

    def delete(self, category_id):
        """Delete a category by ID."""
        with get_db_connection() as (conn, cursor):
            category = fetch_category_by_id(cursor, category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            cursor.execute("DELETE FROM categories WHERE id=?", (category_id,))
            conn.commit()

            return category, 200
