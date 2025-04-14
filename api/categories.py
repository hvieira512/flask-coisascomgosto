from flask import Blueprint, jsonify, request

from .utils import (
    execute,
    fetch_all,
    fetch_one,
)

bp = Blueprint("category", __name__)


@bp.route("/categories", methods=["GET"])
def get_categories():
    categories = fetch_all("SELECT * FROM categories")

    return jsonify(
        [{"id": category.id, "name": category.name} for category in categories]
    )


@bp.route("/category/<int:id>", methods=["GET"])
def get_category(id):
    category = fetch_one("SELECT * FROM categories WHERE id=?", (id))

    id, name = category

    return jsonify({"id": id, "name": name})


@bp.route("/category", methods=["POST"])
def create_category():
    def validate(data):
        for item in data:
            print(item)

    data = request.get_json()

    validate(data)

    category = data["category"]

    if fetch_one("SELECT 1 FROM categories WHERE name=?", (category)):
        return jsonify({"error": "This category already exists!"}), 400

    execute("INSERT INTO categories (name) VALUES (?)", (category))

    inserted = fetch_one(
        "SELECT 1 FROM categories WHERE name=? ORDER BY DESC", (category)
    )

    inserted_id, inserted_name = inserted

    return jsonify(
        {
            "success": "Category was successfully created.",
            "category": {
                "id": inserted_id,
                "name": inserted_name,
            },
        }
    )


@bp.route("/category/<int:id>", methods=["PUT"])
def update_category(id):
    data = request.get_json()

    err = validate_json_fields(data, {"name": str})
    if err:
        return err

    name = data["name"]

    if not fetch_one("SELECT 1 FROM categories WHERE id=?", (name)):
        return jsonify({"error": "Invalid category"}), 404

    if fetch_one("SELECT 1 FROM categories WHERE id<>? AND name=?", (id, name)):
        return jsonify({"error": f"Category {name} already exists."}), 400

    execute("UPDATE categories SET name = ? WHERE id=?", (name, id))

    return jsonify(
        {
            "success": f"Category #{id} was successfully updated.",
            "category": {"id": id, "name": name},
        }
    )


@bp.route("/category/<int:id>", methods=["PATCH"])
def disable_category(id):
    category = fetch_one("SELECT name FROM categories WHERE id=?", (id))

    name = category

    if category is None:
        return jsonify({"error": "Invalid category"}), 404

    execute("UPDATE categories SET enabled=0 WHERE id=?", (id))

    return jsonify(
        {
            "success": f"Category {name} was successfully disabled.",
            "category": {"id": id, "name": name},
        }
    )
