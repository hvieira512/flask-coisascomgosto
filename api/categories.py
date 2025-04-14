from flask import Blueprint, jsonify, request

from .utils import build_insert_query, fetch_all, fetch_one, execute

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


def category_exists_id(id: int) -> bool:
    category = fetch_one("SELECT COUNT(*) FROM categories WHERE id=?", (id,))
    return category[0] > 0


def category_exists_name(name: str) -> bool:
    category = fetch_one("SELECT COUNT(*) FROM categories WHERE name=?", (name,))
    return category[0] > 0


# ----------------
# Route handlers
# ----------------


@bp.route("/", methods=["GET"])
def get_categories():
    categories = fetch_all("SELECT * FROM categories")

    return jsonify([dict(category) for category in categories])


@bp.route("/<int:id>", methods=["GET"])
def get_category(id: int):
    category = fetch_one("SELECT * FROM categories WHERE id = ?", (id,))

    if not category:
        return jsonify({"error": "Category not found"}), 404

    return jsonify(dict(category))


@bp.route("/", methods=["POST"])
def create_category():
    data = request.get_json()
    error = validate_json(data)
    if error:
        return error

    name = data["name"]

    if category_exists_name(name):
        return jsonify({"error": "Category already exists."}), 409

    try:
        id = execute("INSERT INTO categories (name) VALUES (?)", (name,))
        return jsonify({"id": id, "name": name}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["PUT"])
def update_category(id: int):
    data = request.get_json()
    validate_json(data)

    if not category_exists_id(id):
        return jsonify({"error": "Invalid category."})

    name = data.get("name")

    execute("UPDATE categories SET name = ? WHERE id = ?", (name, id))
    updated = fetch_one("SELECT * FROM categories WHERE id = ?", (id,))

    return jsonify({"message": "Category updated", "category": dict(updated)})


@bp.route("/<int:id>", methods=["DELETE"])
def delete_category(id: int):
    if not category_exists_id(id):
        return jsonify({"error": "Invalid category"})

    deleted = fetch_one("SELECT * FROM categories WHERE id=?", (id))

    execute("DELETE FROM categories WHERE id = ?", (id,))

    return jsonify({"message": f"Category {id} deleted.", "category": dict(deleted)})
