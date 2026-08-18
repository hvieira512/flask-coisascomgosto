import click
from flask import Flask
from flask_jwt_extended import JWTManager

from api import api
from api.db import init_db
from config import Config
from web import register_web

app = Flask(__name__)
app.config.from_object(Config)

JWTManager(app)
api.init_app(app)
register_web(app)


@app.cli.command("init-db")
def init_db_command():
    """Create the database and (re)create every table."""
    init_db()


@app.cli.command("seed")
def seed_command():
    """Fill the catalog with development data."""
    from db.seed import seed

    seed()


@app.cli.command("create-admin")
@click.argument("username")
@click.option("--email", prompt=True, help="Used for the account only; nothing is sent.")
@click.password_option(help="Prompted for, so it stays out of your shell history.")
def create_admin_command(username, email, password):
    """Create an administrator account.

    The password is prompted for and hashed here; it is never passed as an
    argument, so it does not end up in the shell history or the process list.
    """
    from werkzeug.security import generate_password_hash

    from api.db import get_db_connection
    from api.repositories import UserRepository

    with get_db_connection() as (_, cursor):
        users = UserRepository(cursor)

        if users.username_exists(username):
            raise click.ClickException(f"The username {username} is already taken.")
        if users.email_exists(email):
            raise click.ClickException(f"The e-mail {email} is already taken.")

        users.create(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
        )

    click.echo(f"Administrator created: {username}")


if __name__ == "__main__":
    app.run()
