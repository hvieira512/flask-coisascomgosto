"""The entry point: build the app, and nothing else.

The five `flask …` commands used to live here and made this file 145 lines, of
which fifteen were the application. They are in cli.py.
"""

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
