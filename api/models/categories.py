from flask_restx import Model, fields

from api.models.common import pagination_model

category_model = Model(
    "Category",
    {
        "id": fields.Integer(readOnly=True, description="Category ID"),
        "name": fields.String(required=True, description="Category Name"),
    },
)

category_list_model = Model(
    "CategoryList",
    {
        "categories": fields.List(fields.Nested(category_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

category_create_model = Model(
    "CategoryCreateModel",
    {
        "name": fields.String(required=True, description="Category Name"),
    },
)
