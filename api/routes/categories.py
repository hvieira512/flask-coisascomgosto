from flask import request
from flask_restx import Namespace, Resource

from api.helpers.categories import (
    category_exists_by_id,
    category_exists_by_name,
    category_name_taken,
    fetch_category_by_id,
)
from api.helpers.pagination import get_pagination_params, make_pagination
from api.models.common import pagination_model
from api.models.categories import (
    category_list_model,
    category_model,
    category_create_model,
)
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
    def get(self):
        """Get list of categories with pagination."""
        page, limit, offset = get_pagination_params(request.args)

        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT COUNT(*) FROM categories")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT * FROM categories LIMIT ? OFFSET ?", (limit, offset))
            categories = [dict(row) for row in cursor.fetchall()]

            return {
                "categories": categories,
                "pagination": make_pagination(total, page, limit),
            }
        finally:
            cursor.close()
            conn.close()

    @ns.expect(category_create_model, validate=True)
    @ns.marshal_with(category_model, code=201)
    def post(self):
        """Create a new category."""
        data = request.get_json()
        name = data["name"]

        conn, cursor = get_db_connection()
        try:
            if category_exists_by_name(cursor, name):
                ns.abort(409, f"The category '{name}' already exists.")

            cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            category_id = cursor.lastrowid
            conn.commit()

            category = fetch_category_by_id(cursor, category_id)
            return category, 201
        finally:
            cursor.close()
            conn.close()


@ns.route("/<int:category_id>")
class Category(Resource):
    @ns.marshal_with(category_model)
    def get(self, category_id):
        """Get a category by ID."""
        conn, cursor = get_db_connection()
        try:
            category = fetch_category_by_id(cursor, category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            return category
        finally:
            cursor.close()
            conn.close()

    @ns.expect(category_model, validate=True)
    @ns.marshal_with(category_model)
    def put(self, category_id):
        """Update a category by ID."""
        data = request.get_json()
        name = data.get("name")

        conn, cursor = get_db_connection()
        try:
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
            return category
        finally:
            cursor.close()
            conn.close()

    def delete(self, category_id):
        """Delete a category by ID."""
        conn, cursor = get_db_connection()
        try:
            category = fetch_category_by_id(cursor, category_id)
            if not category:
                ns.abort(404, f"Category #{category_id} not found")

            cursor.execute("DELETE FROM categories WHERE id=?", (category_id,))
            conn.commit()

            return {"message": f"Category #{category_id} deleted", "category": category}
        finally:
            cursor.close()
            conn.close()
