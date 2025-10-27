from flask_restx import Model, fields

user_model = Model(
    "User",
    {
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="User E-mail"),
        "is_admin": fields.Boolean(default=False, description="Is the user an admin"),
        "created_at": fields.DateTime(description="Datetime creation of the account"),
    },
)
