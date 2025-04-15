from flask import Blueprint, jsonify, request

from api.categories import category_id_exists

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


def product_exists_id(id: int) -> bool:
    category = fetch_one("SELECT COUNT(*) FROM products WHERE id=?", (id,))
    return category[0] > 0


def product_exists_name(name: str) -> bool:
    category = fetch_one("SELECT COUNT(*) FROM products WHERE name=?", (name,))
    return category[0] > 0


# ----------------
# Route handlers
# ----------------


@bp.route("/", methods=["GET"])
def get_products():
    products = fetch_all("SELECT * FROM products")

    return jsonify([dict(product) for product in products])


@bp.route("/<int:id>", methods=["GET"])
def get_product(id: int):
    product = fetch_one("SELECT * FROM products WHERE id = ?", (id,))

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

    if not category_id_exists(data["category"]):
        return jsonify({"error": "Invalid category."}), 409

    if product_exists_name(data["name"]):
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

    if not product_exists_id(id):
        return jsonify({"error": "Product not found."}), 404

    if product_exists_name(data["name"]):
        return jsonify({"error": "Product name already exists."}), 409

    try:
        query, values = build_update_query("products", data, "id = ?", (id,))
        execute(query, values)
        updated = fetch_one("SELECT * FROM products WHERE id = ?", (id,))
        return jsonify({"message": "Product updated", "product": dict(updated)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["DELETE"])
def delete_category(id: int):
    if not product_exists_id(id):
        return jsonify({"error": "Invalid product."})

    deleted = fetch_one("SELECT * FROM products WHERE id=?", (id,))

    try:
        execute("DELETE FROM products WHERE id=?", (id,))
        return jsonify({"message": f"Product {id} deleted.", "product": dict(deleted)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
