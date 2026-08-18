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


@app.cli.command("migrate")
@click.option("--status", "show_status", is_flag=True,
              help="List what is applied and what is pending, and change nothing.")
@click.option("--stamp", is_flag=True,
              help="Record every migration as applied without running any of it, "
                   "for a database that is already up to date.")
def migrate_command(show_status, stamp):
    """Apply the pending migrations in db/migrations."""
    from api import migrations

    if stamp:
        stamped = migrations.stamp_all()
        click.echo(f"Recorded {stamped} migration(s) as applied without running them.")
        return

    if show_status:
        rows = migrations.status()
        if not rows:
            click.echo("No migrations.")
            return
        for filename, applied in rows:
            click.echo(f"  {'applied' if applied else 'pending'}  {filename}")
        return

    applied = migrations.apply_pending()
    if not applied:
        click.echo("Nothing to apply; the database is up to date.")
        return

    for filename in applied:
        click.echo(f"Applied {filename}")


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
