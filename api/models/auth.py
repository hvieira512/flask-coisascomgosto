from flask_restx import Model, fields

login_model = Model(
    "Login",
    {
        "username": fields.String(required=True, description="Username"),
        "password": fields.String(required=True, description="User Password"),
    },
)

register_model = Model(
    "Register",
    {
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="User E-mail"),
        "password": fields.String(required=True, description="User Password"),
        "is_admin": fields.Boolean(default=False, description="Is the user an admin"),
    },
)
