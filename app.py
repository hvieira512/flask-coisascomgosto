import os

from datetime import date
from flask import Flask
from flask_cors import CORS

from api import api_bp
from api.utils import init_db, print_routes
from web import web_bp

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app)

app.register_blueprint(api_bp)
app.register_blueprint(web_bp)

init_db()

print_routes("api", app)
print_routes("web", app)


@app.context_processor
def inject_globals():
    return {"year": date.today().strftime("%Y")}


if __name__ == "__main__":
    app.run()
