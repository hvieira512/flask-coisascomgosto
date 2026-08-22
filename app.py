from flask import Flask
from flask_jwt_extended import JWTManager

from api import api
from cli import register_commands
from config import Config
from web import register_web

app = Flask(__name__)
app.config.from_object(Config)

JWTManager(app)
api.init_app(app)
register_web(app)
register_commands(app)


if __name__ == "__main__":
    app.run()
