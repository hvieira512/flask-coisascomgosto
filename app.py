from datetime import date

from flask import Flask

from api import api_bp
from api.utils import init_db, print_routes
from config import Config
from extensions import cors, mail
from web import web_bp

app = Flask(__name__)
app.config.from_object(Config)

cors.init_app(app)
mail.init_app(app)

app.register_blueprint(api_bp)
app.register_blueprint(web_bp)

app.jinja_env.globals["year"] = date.today().strftime("%Y")

init_db()

print_routes("api", app)
print_routes("web", app)


if __name__ == "__main__":
    app.run()
