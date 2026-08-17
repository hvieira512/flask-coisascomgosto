from flask_restx import Model, fields

from api.models.common import list_model

user_model = Model(
    "User",
    {
        "id": fields.Integer(readOnly=True, description="User ID"),
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="User E-mail"),
        "is_admin": fields.Boolean(default=False, description="Is the user an admin"),
        "created_at": fields.DateTime(description="Datetime creation of the account"),
    },
)

user_list_model = list_model("UserList", "users", user_model)
