from flask import Flask

from api import api
from api.db import init_db
from config import Config
from extensions import cors, jwt, mail
from web import register_web

app = Flask(__name__)
app.config.from_object(Config)

cors.init_app(app)
mail.init_app(app)
jwt.init_app(app)
api.init_app(app)
register_web(app)


@app.cli.command("init-db")
def init_db_command():
    """Create the database and (re)create every table."""
    init_db()


if __name__ == "__main__":
    app.run()
