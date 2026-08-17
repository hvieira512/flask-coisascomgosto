from flask_restx import Model, fields

from api.models.common import list_model

category_model = Model(
    "Category",
    {
        "id": fields.Integer(readOnly=True, description="Category ID"),
        "name": fields.String(required=True, description="Category Name"),
    },
)

category_list_model = list_model("CategoryList", "categories", category_model)

category_create_model = Model(
    "CategoryCreateModel",
    {
        "name": fields.String(required=True, description="Category Name"),
    },
)
