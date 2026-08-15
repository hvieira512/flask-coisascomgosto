from flask_restx import Model, fields

from api.models.users import user_model

login_model = Model(
    "Login",
    {
        "username": fields.String(required=True, description="Username"),
        "password": fields.String(required=True, description="User Password"),
    },
)

# Note: is_admin is intentionally absent. Accepting it here would let any
# caller register themselves as an administrator.
register_model = Model(
    "Register",
    {
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="User E-mail"),
        "password": fields.String(required=True, description="User Password"),
    },
)

# The refresh token travels in the Authorization header, not the body; this
# model exists so the endpoint documents an empty body rather than none.
refresh_model = Model("Refresh", {})

token_model = Model(
    "TokenPair",
    {
        "access_token": fields.String(
            description="Short-lived bearer token for API calls"
        ),
        "refresh_token": fields.String(
            description="Long-lived token used to mint a new access token. "
            "Null on /auth/refresh, which reuses the one you sent."
        ),
        "user": fields.Nested(
            user_model, description="The authenticated account", allow_null=True
        ),
    },
)
