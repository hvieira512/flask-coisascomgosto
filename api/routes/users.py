from flask import request
from flask_restx import Namespace, Resource

from api.db import get_db_connection
from api.models.common import pagination_model
from api.models.users import user_list_model, user_model
from api.pagination import get_pagination_params, make_pagination
from api.repositories import UserRepository
from api.security import PROTECTED_DOC, token_required

ns = Namespace(
    "users",
    description="Users operations. Every endpoint requires a bearer token.",
)

for model in [pagination_model, user_model, user_list_model]:
    ns.models[model.name] = model


@ns.route("/")
class UserList(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(user_list_model)
    @ns.param("page", "Page number, 1-based (default 1)")
    @ns.param("limit", "Items per page, max 100 (default 10)")
    @ns.response(200, "A page of users")
    @ns.response(400, "Invalid pagination parameters")
    @token_required
    def get(self):
        """Get list of users with pagination."""
        page, limit, offset = get_pagination_params(request.args)

        with get_db_connection() as (_, cursor):
            users = UserRepository(cursor)

            return {
                "users": users.list(limit=limit, offset=offset),
                "pagination": make_pagination(users.count(), page, limit),
            }


@ns.route("/<int:user_id>")
class User(Resource):
    @ns.doc(**PROTECTED_DOC)
    @ns.marshal_with(user_model)
    @ns.response(200, "The user")
    @ns.response(404, "User not found")
    @token_required
    def get(self, user_id):
        """Get a user by ID."""
        with get_db_connection() as (_, cursor):
            user = UserRepository(cursor).get(user_id)
            if not user:
                ns.abort(404, f"User #{user_id} not found")

            return user
