from flask import Blueprint, jsonify

from utils import fetch_all


bp = Blueprint("product", __name__)


@bp.route("/products", methods=["GET"])
def get_products():
    products = fetch_all("SELECT id, name, category FROM products")

    return jsonify(
        [
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
            }
            for product in products
        ]
    )


@bp.route("/product/<int:id>", methods=["GET"])
def get_product(id):
    return jsonify({"success": f"GET #{id} Product"})


@bp.route("/product", methods=["POST"])
def create_product():
    return jsonify({"success": "POST Product"})


@bp.route("/product/<int:id>", methods=["PUT"])
def update_product(id):
    return jsonify({"success": f"PUT #{id} Product"})


@bp.route("/product/<int:id>", methods=["DELETE"])
def delete_product(id):
    return jsonify({"success": f"DELETE #{id} Product"})
