from datetime import date

from flask import Flask

from api import api
from api.utils import init_db
from config import Config
from extensions import cors, mail
from web import web_bp

app = Flask(__name__)
app.config.from_object(Config)

cors.init_app(app)
mail.init_app(app)
api.init_app(app)

app.register_blueprint(web_bp)

app.jinja_env.globals["year"] = date.today().strftime("%Y")


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database."""
    init_db()


print(app.url_map)


if __name__ == "__main__":
    app.run()
