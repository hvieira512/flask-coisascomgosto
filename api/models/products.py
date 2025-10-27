from flask_restx import Model, fields

from api.models.common import pagination_model
from api.models.categories import category_model

product_model = Model(
    "Product",
    {
        "id": fields.Integer(readOnly=True, description="Product ID"),
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, descritpion="Product Description"),
        "category": fields.Nested(category_model),
    },
)

product_list_model = Model(
    "ProductList",
    {
        "products": fields.List(fields.Nested(product_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

product_create_model = Model(
    "ProductCreate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "category_id": fields.Integer(required=True, description="Product Category ID"),
    },
)

update_product_model = Model(
    "ProductUpdate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "category_id": fields.Integer(required=True, description="Product Category ID"),
    },
)
