from flask import request
from flask_restx import Namespace, Resource

from api.helpers.categories import category_exists_by_id
from api.helpers.pagination import get_pagination_params, make_pagination
from api.helpers.products import (
    build_product_filters,
    fetch_product_by_id,
    product_exists_by_name,
    product_name_taken,
)
from api.models.products import (
    product_create_model,
    product_list_model,
    product_model,
    update_product_model,
)
from api.utils import get_db_connection

ns = Namespace("products", description="Products operations")

ns.models[product_model.name] = product_model
ns.models[product_list_model.name] = product_list_model
ns.models[product_create_model.name] = product_create_model
ns.models[update_product_model.name] = update_product_model


@ns.route("/")
class ProductList(Resource):
    @ns.marshal_with(product_list_model)
    @ns.param("q", "Search term for category name or product name (fuzzy search)")
    def get(self):
        page, limit, offset = get_pagination_params(request.args)
        where_clause, params = build_product_filters(request.args)

        with get_db_connection() as (_, cursor):
            cursor.execute(f"SELECT COUNT(*) FROM products {where_clause}", params)
            total = cursor.fetchone()[0]

            query = f"""
                SELECT 
                    p.id AS id,
                    p.name AS name,
                    p.description AS description,
                    c.id AS category_id,
                    c.name AS category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                {where_clause}
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            products = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "category": {
                        "id": r["category_id"],
                        "name": r["category_name"],
                    },
                }
                for r in cursor.fetchall()
            ]

            return {
                "products": products,
                "pagination": make_pagination(total, page, limit),
            }

    @ns.expect(product_create_model, validate=True)
    @ns.marshal_with(product_model, code=201)
    def post(self):
        data = ns.payload

        category_id = data["category_id"]
        name = data["name"]
        description = data["description"]

        with get_db_connection() as (conn, cursor):
            if not category_exists_by_id(cursor, category_id):
                ns.abort(404, f"The category #{category_id} does not exist.")

            if product_exists_by_name(cursor, name):
                ns.abort(409, f"The product {name} already exists.")

            cursor.execute(
                "INSERT INTO products (category_id, name, description) VALUES (?, ?, ?)",
                (category_id, name, description),
            )
            product_id = cursor.lastrowid
            conn.commit()

            product = fetch_product_by_id(cursor, product_id)
            return product, 201


@ns.route("/<int:product_id>")
class Product(Resource):
    @ns.marshal_with(product_model)
    def get(self, product_id):
        with get_db_connection() as (_, cursor):
            product = fetch_product_by_id(cursor, product_id)
            if not product:
                ns.abort(404, f"Product #{product_id} not found")

            return product
        pass

    @ns.expect(update_product_model)
    @ns.marshal_with(product_model)
    def put(self, product_id):
        data = ns.payload

        category_id = data["category_id"]
        name = data["name"]
        description = data["description"]

        with get_db_connection() as (conn, cursor):
            if not category_exists_by_id(cursor, category_id):
                ns.abort(404, f"The category #{category_id} was not found.")

            if product_name_taken(cursor, name, product_id):
                ns.abort(
                    409, f"Product name '{name}' is already used by another product"
                )

            cursor.execute(
                "UPDATE products SET category_id = ?, name = ?, description = ? WHERE id = ?",
                (category_id, name, description, product_id),
            )
            conn.commit()

            product = fetch_product_by_id(cursor, product_id)
            return product, 200

    @ns.marshal_with(product_model)
    def delete(self, product_id):
        with get_db_connection() as (conn, cursor):
            product = fetch_product_by_id(cursor, product_id)
            if not product:
                ns.abort(404, f"Category #{product_id} not found")

            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()

            return product, 200
