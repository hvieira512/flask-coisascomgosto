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


def list_model(name: str, key: str, model: Model) -> Model:
    """The envelope every list endpoint returns: the rows, and the page they
    came from. Nine resources declared this identically."""
    return Model(
        name,
        {
            key: fields.List(fields.Nested(model)),
            "pagination": fields.Nested(pagination_model),
        },
    )
