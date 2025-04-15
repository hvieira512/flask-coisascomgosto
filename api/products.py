from flask import Blueprint, jsonify, request

from api.categories import get_category_by_id

from .utils import (
    build_update_query,
    fetch_all,
    fetch_one,
    execute,
)

bp = Blueprint("products", __name__)

# ----------------
# Helper functions
# ----------------


def validate_json(data):
    expected = {
        "name": "Product name",
        "category": 14,
        "description": "Optional description text.",
    }

    if "name" not in data or not isinstance(data["name"], str):
        return jsonify(
            {
                "error": "Field 'name' is required and must be a string.",
                "expected": expected,
            }
        ), 400

    if "category" not in data or not isinstance(data["category"], int):
        return jsonify(
            {
                "error": "Field 'category' is required and must be an integer.",
                "expected": expected,
            }
        ), 400

    if "description" in data and not isinstance(data["description"], str):
        return jsonify(
            {
                "error": "Field 'description' must be a string",
                "expected": expected,
            }
        )

    return None


def get_product_by_id(id: int):
    product = fetch_one("SELECT * FROM products WHERE id = ?", (id,))
    if product:
        return dict(product)
    return None


def product_id_exists(id: int) -> bool:
    query = "SELECT COUNT(*) FROM products WHERE id=?"
    return fetch_one(query, (id,)) is not None


def product_name_exists(name: str) -> bool:
    query = "SELECT COUNT(*) FROM products WHERE name=?"
    return fetch_one(query, (name,)) is not None


def product_name_taken(name: str, id: int) -> bool:
    query = "SELECT COUNT(*) FROM products WHERE name=? AND id<>? "
    return fetch_one(query, (name, id))


# ----------------
# Route handlers
# ----------------


@bp.route("/", methods=["GET"])
def get_products():
    products = fetch_all("SELECT * FROM products")

    return jsonify([dict(product) for product in products])


@bp.route("/<int:id>", methods=["GET"])
def get_product(id: int):
    product = get_product_by_id(id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(dict(product))


@bp.route("/", methods=["POST"])
def create_product():
    data = request.get_json()
    error = validate_json(data)
    if error:
        return error

    category = data["category"]
    name = data["name"]
    description = data.get("description")

    if not get_category_by_id(category):
        return jsonify({"error": "Invalid category."}), 409

    if product_name_exists(data["name"]):
        return jsonify({"error": "Product already exists."}), 409

    try:
        id = execute(
            "INSERT INTO products (category_id, name, description) VALUES (?, ?, ?)",
            (category, name, description),
        )
        return jsonify({"id": id, "name": name, "description": description}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["PUT"])
def update_product(id: int):
    data = request.get_json()
    error = validate_json(data)
    if error:
        return error

    name = data["name"]

    if not product_id_exists(id):
        return jsonify({"error": "Product not found."}), 404

    if product_name_taken(name, id):
        return jsonify({"error": "Product name already exists."}), 409

    try:
        query, values = build_update_query("products", data, "id = ?", (id,))
        execute(query, values)

        return jsonify({"message": "Product updated", "product": get_product_by_id(id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["DELETE"])
def delete_category(id: int):
    if not product_id_exists(id):
        return jsonify({"error": "Invalid product."})

    try:
        execute("DELETE FROM products WHERE id=?", (id,))

        return jsonify(
            {"message": f"Product {id} deleted.", "product": get_product_by_id(id)}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
