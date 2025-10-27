from flask_restx import Namespace

from api.models.users import user_model

ns = Namespace("users", description="Users operations")

ns.models[user_model.name] = user_model
