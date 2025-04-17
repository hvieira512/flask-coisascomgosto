from flask import Blueprint, jsonify, request

from .utils import fetch_all, fetch_one, execute

bp = Blueprint("categories", __name__)

# ----------------
# Helper functions
# ----------------


def validate_json(data):
    expected = {"name": "Category name"}

    if "name" not in data or not isinstance(data.get("name"), str):
        return jsonify(
            {
                "error": "Field 'name' is required and must be a string.",
                "expected": expected,
            }
        ), 400

    return None


def get_category_by_id(id: int):
    category = fetch_one("SELECT * FROM categories WHERE id = ?", (id,))
    if category:
        return dict(category)
    return None


def category_name_exists(name: str) -> bool:
    query = "SELECT * FROM categories WHERE name=?"
    return fetch_one(query, (name,)) is not None


def category_name_taken(name: str, id: int) -> bool:
    query = "SELECT * FROM categories WHERE id<>? AND name=?"
    return fetch_one(query, (id, name)) is not None


# ----------------
# Route handlers
# ----------------


@bp.route("")
def get_categories():
    categories = fetch_all("SELECT * FROM categories")
    return jsonify([dict(category) for category in categories])


@bp.route("/<int:id>")
def get_category(id: int):
    category = get_category_by_id(id)
    if not category:
        return jsonify({"error": "Category not found"}), 404
    return jsonify(category)


@bp.route("", methods=["POST"])
def create_category():
    data = request.get_json()
    error = validate_json(data)
    if error:
        return error

    name = data["name"]

    if category_name_exists(name):
        return jsonify({"error": "Category already exists."}), 409

    id = execute("INSERT INTO categories (name) VALUES (?)", (name,))
    if not id:
        return jsonify({"error": "Failed to create category."}), 500

    category = get_category_by_id(id)
    return jsonify(
        {"message": "Category created successfully", "category": category}
    ), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_category(id: int):
    category = get_category_by_id(id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json()
    error = validate_json(data)
    if error:
        return error

    name = data.get("name")

    print(
        "name:",
        name,
        "| current category id:",
        id,
        "| name_taken:",
        category_name_taken(name, id),
    )

    if category_name_taken(name, id):
        return jsonify({"error": "Category name already exists."}), 409

    execute("UPDATE categories SET name=? WHERE id=?", (name, id))

    updated_category = get_category_by_id(id)
    return jsonify({"message": "Category updated", "category": updated_category})


@bp.route("/<int:id>", methods=["DELETE"])
def delete_category(id: int):
    category = get_category_by_id(id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    execute("DELETE FROM categories WHERE id = ?", (id,))
    return jsonify({"message": "Category deleted", "category": category})
