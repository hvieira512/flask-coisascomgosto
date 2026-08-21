from flask_restx import Model, fields

from api.models.users import user_model

login_model = Model(
    "Login",
    {
        "username": fields.String(required=True, description="Username"),
        # Optional so the login page's first step can ask whether an account
        # exists without sending a guess. See Login.post.
        "password": fields.String(
            required=False,
            description="Omit to ask whether the username exists: 404 if not, "
            "401 if it does. No hash is checked and nothing is counted against "
            "the account.",
        ),
    },
)

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
