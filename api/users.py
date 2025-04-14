from flask import Blueprint, jsonify


bp = Blueprint("user", __name__)


@bp.route("/users", methods=["GET"])
def get_users():
    return jsonify({"success": "GET users"})


@bp.route("/user/<int:id>", methods=["GET"])
def get_user(id):
    return jsonify({"success": f"GET #{id} user"})


@bp.route("/user", methods=["POST"])
def create_user():
    return jsonify({"success": "POST user"})


@bp.route("/user/<int:id>", methods=["PUT"])
def update_user(id):
    return jsonify({"success": f"PUT #{id} user"})


@bp.route("/user/<int:id>", methods=["DELETE"])
def delete_user(id):
    return jsonify({"success": f"DELETE #{id} user"})
