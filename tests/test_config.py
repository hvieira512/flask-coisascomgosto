"""The signing keys and the cookie flags.

In a subprocess on purpose. `config.py` decides these at import, so the only
honest way to test "it refuses to start" is to start it — and reloading the
module inside the test process would leave every later test running against
whichever environment the last case happened to set.
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What .env.example ships — a different placeholder per key, which is the reason
# config.py checks a set rather than one string.
DEV_SECRET = "dev-secret-change-me"
DEV_JWT_SECRET = "dev-jwt-secret-change-me"


def _import_config(attr="SECRET_KEY", **env):
    """Import config.py in a fresh interpreter and print `attr`.

    .env is loaded by config itself and supplies FLASK_DEBUG=1 and a placeholder
    for both keys — exactly the combination under test — so each case passes its
    own values in the environment, where dotenv leaves them alone.

    Real secrets are the baseline for the same reason: a case that says nothing
    about JWT_SECRET_KEY should not be failed by the placeholder .env holds for
    it. Overriding one key is then the whole statement of what a case is about.
    """
    return subprocess.run(
        [sys.executable, "-c", f"import config; print(config.Config.{attr})"],
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "SECRET_KEY": "a-real-secret",
            "JWT_SECRET_KEY": "a-real-jwt-secret",
            **env,
        },
        capture_output=True,
        text=True,
    )


class TestTheSigningKeysAreNotOptional:
    """A deployment signing its cookies with a constant from this repository boots
    and serves exactly like a safe one. That is why this is a refusal to start
    rather than a warning in a log nobody reads."""

    def test_it_refuses_the_dev_secret_outside_debug(self):
        result = _import_config(FLASK_DEBUG="0", SECRET_KEY=DEV_SECRET)

        assert result.returncode != 0
        assert "SECRET_KEY" in result.stderr
        # The message has to say what to do, not just that something is wrong.
        assert ".env.example" in result.stderr

    def test_it_refuses_the_dev_jwt_secret_outside_debug(self):
        """The JWT placeholder is a different string from the session one, so a
        guard that only knew the session value would let this one through."""
        result = _import_config(FLASK_DEBUG="0", JWT_SECRET_KEY=DEV_JWT_SECRET)

        assert result.returncode != 0
        assert "JWT_SECRET_KEY" in result.stderr

    def test_a_real_secret_starts(self):
        result = _import_config(FLASK_DEBUG="0")

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "a-real-secret"

    def test_development_still_runs_on_the_placeholder(self):
        """Otherwise the guard would be something every developer works around,
        which is the same as not having it. This is the .env in the repository."""
        result = _import_config(
            FLASK_DEBUG="1", SECRET_KEY=DEV_SECRET, JWT_SECRET_KEY=DEV_JWT_SECRET
        )

        assert result.returncode == 0, result.stderr


class TestTheSessionCookieIsTreatedAsACredential:
    """api/security.py accepts the session cookie in place of a bearer token, so
    it can write to the whole catalogue."""

    def test_the_flags_are_set(self):
        from config import Config

        assert Config.SESSION_COOKIE_HTTPONLY is True
        assert Config.SESSION_COOKIE_SAMESITE == "Lax"

    def test_secure_follows_debug(self):
        """No TLS in development, so a Secure cookie there would simply never be
        sent; everywhere else it must not travel in clear."""
        deployed = _import_config("SESSION_COOKIE_SECURE", FLASK_DEBUG="0")
        assert deployed.stdout.strip() == "True", deployed.stderr

        development = _import_config("SESSION_COOKIE_SECURE", FLASK_DEBUG="1")
        assert development.stdout.strip() == "False", development.stderr

    def test_the_body_limit_comes_from_uploads(self):
        """One definition of "too big", so the 413 and the message the owners read
        cannot drift apart."""
        from config import Config
        from uploads import MAX_BYTES

        assert Config.MAX_CONTENT_LENGTH > MAX_BYTES
        # Enough headroom for the multipart envelope, not enough to be a second
        # limit of its own.
        assert Config.MAX_CONTENT_LENGTH <= MAX_BYTES * 2
