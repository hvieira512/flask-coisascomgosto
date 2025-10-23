from flask_restx import Model, fields

pagination_model = Model(
    "Pagination",
    {
        "total": fields.Integer,
        "page": fields.Integer,
        "pages": fields.Integer,
        "limit": fields.Integer,
    },
)
