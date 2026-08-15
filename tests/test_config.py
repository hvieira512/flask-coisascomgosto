"""Settings are read in config.py and nowhere else."""

import importlib
import pathlib

import pytest

import config


class TestTypedReaders:
    def test_int_coerces(self, monkeypatch):
        monkeypatch.setenv("PROBE", "42")
        assert config.env_int("PROBE", 1) == 42

    def test_int_falls_back_when_unset_or_blank(self, monkeypatch):
        monkeypatch.delenv("PROBE", raising=False)
        assert config.env_int("PROBE", 7) == 7
        monkeypatch.setenv("PROBE", "   ")
        assert config.env_int("PROBE", 7) == 7

    def test_int_rejects_garbage_loudly(self, monkeypatch):
        """A typo'd port should fail at startup, not as a confusing later error."""
        monkeypatch.setenv("PROBE", "3306a")
        with pytest.raises(RuntimeError, match="must be an integer"):
            config.env_int("PROBE", 3306)

    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
    def test_bool_truthy(self, monkeypatch, raw):
        monkeypatch.setenv("PROBE", raw)
        assert config.env_bool("PROBE") is True

    @pytest.mark.parametrize("raw", ["0", "false", "no", "off", ""])
    def test_bool_falsey(self, monkeypatch, raw):
        monkeypatch.setenv("PROBE", raw)
        assert config.env_bool("PROBE") is False


class TestDatabaseConfig:
    def test_reads_the_environment_each_call(self, monkeypatch):
        """The test suite repoints MYSQL_DATABASE after import, so these must
        not be captured at import time."""
        monkeypatch.setenv("MYSQL_DATABASE", "somewhere_else")
        assert config.database_config()["database"] == "somewhere_else"

    def test_port_is_an_int(self, monkeypatch):
        monkeypatch.setenv("MYSQL_PORT", "3307")
        assert config.database_config()["port"] == 3307

    def test_omits_the_schema_when_asked(self):
        assert "database" not in config.database_config(database=False)


class TestProductionSecrets:
    def test_dev_secrets_are_refused_outside_debug(self, monkeypatch):
        monkeypatch.setattr(config.Config, "DEBUG", False)
        monkeypatch.setattr(config.Config, "SECRET_KEY", config.DEV_SECRET)
        monkeypatch.setattr(config.Config, "JWT_SECRET_KEY", "something-real")

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            config.check_production_secrets()

    def test_dev_secrets_are_fine_in_debug(self, monkeypatch):
        monkeypatch.setattr(config.Config, "DEBUG", True)
        monkeypatch.setattr(config.Config, "SECRET_KEY", config.DEV_SECRET)
        config.check_production_secrets()

    def test_real_secrets_pass(self, monkeypatch):
        monkeypatch.setattr(config.Config, "DEBUG", False)
        monkeypatch.setattr(config.Config, "SECRET_KEY", "a-real-secret")
        monkeypatch.setattr(config.Config, "JWT_SECRET_KEY", "another-real-secret")
        config.check_production_secrets()


class TestSingleSourceOfTruth:
    def test_no_module_reads_the_environment_directly(self):
        """Settings belong in config.py; conftest is the one exception, since it
        repoints the database before anything imports it."""
        offenders = []
        for path in list(pathlib.Path("api").rglob("*.py")) + \
                    list(pathlib.Path("web").rglob("*.py")) + \
                    [pathlib.Path("app.py")]:
            if "__pycache__" in str(path):
                continue
            text = path.read_text()
            if "os.environ" in text or "os.getenv" in text:
                offenders.append(str(path))
        assert offenders == [], offenders

    def test_dotenv_is_loaded_once(self):
        """Two load_dotenv() calls used to paper over import ordering."""
        loaders = [
            str(p)
            for p in [pathlib.Path("config.py"), pathlib.Path("app.py")]
            + list(pathlib.Path("api").rglob("*.py"))
            + list(pathlib.Path("web").rglob("*.py"))
            if "__pycache__" not in str(p) and "load_dotenv()" in p.read_text()
        ]
        assert loaders == ["config.py"], loaders
