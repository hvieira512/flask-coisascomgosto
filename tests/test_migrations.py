"""The migration runner.

Every one of these points a temporary directory at the runner rather than using
the project's real migrations, so the suite tests the mechanism and not the
history — and adding a migration to db/migrations never breaks these.
"""

import pytest

from db import migrate as migrations
from db import get_db_connection


PROBE_TABLES = ["probe_one", "probe_two", "probe_order", "probe_dml"]


def _drop_probes():
    with get_db_connection() as (_, cursor):
        for table in PROBE_TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")


@pytest.fixture()
def migrations_dir(tmp_path, monkeypatch):
    """An empty migrations directory and an empty ledger.

    The tables these migrations create are dropped either side: clean_database
    truncates tables, it does not drop them, so a probe table would survive into
    the next test and its CREATE would fail as a duplicate.
    """
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)
    _drop_probes()
    with get_db_connection() as (_, cursor):
        cursor.execute("DROP TABLE IF EXISTS schema_migrations")

    yield tmp_path

    _drop_probes()


def write(directory, name, sql):
    (directory / name).write_text(sql, encoding="utf-8")


def table_exists(name):
    with get_db_connection() as (_, cursor):
        cursor.execute("SHOW TABLES LIKE %s", (name,))
        return cursor.fetchone() is not None


def applied_names():
    return [name for name, applied in migrations.status() if applied]


class TestApplying:
    def test_applies_a_pending_migration(self, migrations_dir):
        write(migrations_dir, "0001_add_a_table.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")

        assert migrations.apply_pending() == ["0001_add_a_table.sql"]
        assert table_exists("probe_one")

    def test_records_what_it_applied(self, migrations_dir):
        write(migrations_dir, "0001_add_a_table.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")
        migrations.apply_pending()

        assert applied_names() == ["0001_add_a_table.sql"]

    def test_does_not_apply_the_same_file_twice(self, migrations_dir):
        """The whole point: running migrate again is safe."""
        write(migrations_dir, "0001_add_a_table.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")
        migrations.apply_pending()

        # A second run must not re-execute the CREATE, which would raise.
        assert migrations.apply_pending() == []

    def test_runs_them_in_numbered_order(self, migrations_dir):
        """0010 after 0002, which is what the zero padding is for."""
        write(migrations_dir, "0002_first.sql",
              "CREATE TABLE probe_order (id INT PRIMARY KEY);")
        write(migrations_dir, "0010_second.sql",
              "ALTER TABLE probe_order ADD COLUMN name VARCHAR(20);")

        assert migrations.apply_pending() == ["0002_first.sql", "0010_second.sql"]

    def test_applies_only_what_is_new(self, migrations_dir):
        write(migrations_dir, "0001_one.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")
        migrations.apply_pending()

        write(migrations_dir, "0002_two.sql",
              "CREATE TABLE probe_two (id INT PRIMARY KEY);")
        assert migrations.apply_pending() == ["0002_two.sql"]

    def test_a_multi_statement_file_runs_every_statement(self, migrations_dir):
        write(migrations_dir, "0001_two_things.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);\n"
              "CREATE TABLE probe_two (id INT PRIMARY KEY);")
        migrations.apply_pending()

        assert table_exists("probe_one")
        assert table_exists("probe_two")

    def test_comments_do_not_become_statements(self, migrations_dir):
        """The files carry their reasoning, which must not reach the server."""
        write(migrations_dir, "0001_commented.sql",
              "-- why this exists; and a semicolon in the prose\n"
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")

        assert migrations.apply_pending() == ["0001_commented.sql"]
        assert table_exists("probe_one")

    def test_accented_sql_survives(self, migrations_dir):
        """0002 renames a size to "Médio"; the file is read as UTF-8."""
        write(migrations_dir, "0001_accented.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY, name VARCHAR(20));\n"
              "INSERT INTO probe_one (id, name) VALUES (1, 'Médio');")
        migrations.apply_pending()

        with get_db_connection() as (_, cursor):
            cursor.execute("SELECT name FROM probe_one WHERE id = 1")
            assert cursor.fetchone()["name"] == "Médio"


class TestFailure:
    def test_a_failing_migration_is_not_recorded(self, migrations_dir):
        """Otherwise the fix would be skipped as already applied."""
        write(migrations_dir, "0001_broken.sql", "NOT VALID SQL AT ALL;")

        with pytest.raises(Exception):
            migrations.apply_pending()

        assert applied_names() == []

    def test_a_failing_migration_stops_the_ones_after_it(self, migrations_dir):
        """Order is the only guarantee a migration has; carrying on past a
        failure would apply a change to a schema that never got the one before."""
        write(migrations_dir, "0001_broken.sql", "NOT VALID SQL AT ALL;")
        write(migrations_dir, "0002_would_be_fine.sql",
              "CREATE TABLE probe_two (id INT PRIMARY KEY);")

        with pytest.raises(Exception):
            migrations.apply_pending()

        assert not table_exists("probe_two")

    def test_dml_rolls_back(self, migrations_dir):
        """A rename that fails halfway leaves nothing behind. DDL cannot promise
        this — MySQL commits it implicitly — which is why the runner's docstring
        asks for one logical change per file."""
        with get_db_connection() as (_, cursor):
            cursor.execute("CREATE TABLE probe_dml (id INT PRIMARY KEY, name VARCHAR(20))")
            cursor.execute("INSERT INTO probe_dml (id, name) VALUES (1, 'antes')")

        write(migrations_dir, "0001_half_broken.sql",
              "UPDATE probe_dml SET name = 'depois' WHERE id = 1;\n"
              "UPDATE probe_dml SET nonexistent_column = 1;")

        with pytest.raises(Exception):
            migrations.apply_pending()

        with get_db_connection() as (_, cursor):
            cursor.execute("SELECT name FROM probe_dml WHERE id = 1")
            assert cursor.fetchone()["name"] == "antes"


class TestStamping:
    """init-db builds from schema.sql, which already contains everything the
    migrations do, so they are recorded rather than run."""

    def test_stamping_records_without_running(self, migrations_dir):
        write(migrations_dir, "0001_add_a_table.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")

        assert migrations.stamp_all() == 1
        assert applied_names() == ["0001_add_a_table.sql"]
        assert not table_exists("probe_one"), "stamping must not execute the file"

    def test_stamping_twice_is_not_an_error(self, migrations_dir):
        """init-db is re-runnable, so stamping has to be too."""
        write(migrations_dir, "0001_add_a_table.sql", "SELECT 1;")
        migrations.stamp_all()

        assert migrations.stamp_all() == 0
        assert applied_names() == ["0001_add_a_table.sql"]

    def test_migrate_is_a_no_op_after_stamping(self, migrations_dir):
        write(migrations_dir, "0001_add_a_table.sql",
              "CREATE TABLE probe_one (id INT PRIMARY KEY);")
        migrations.stamp_all()

        assert migrations.apply_pending() == []


class TestStatus:
    def test_lists_applied_and_pending_in_order(self, migrations_dir):
        write(migrations_dir, "0001_done.sql", "SELECT 1;")
        write(migrations_dir, "0002_todo.sql", "SELECT 1;")
        migrations.stamp_all()
        write(migrations_dir, "0003_also_todo.sql", "SELECT 1;")

        assert migrations.status() == [
            ("0001_done.sql", True),
            ("0002_todo.sql", True),
            ("0003_also_todo.sql", False),
        ]

    def test_no_migrations_is_not_an_error(self, migrations_dir):
        assert migrations.status() == []
        assert migrations.apply_pending() == []
        assert migrations.stamp_all() == 0


class TestTheRealMigrations:
    """The project's own files, checked for the things that make a history
    reliable rather than for what they contain."""

    def test_every_file_is_numbered_and_unique(self):
        import re

        from db.migrate import MIGRATIONS_DIR

        paths = sorted(MIGRATIONS_DIR.glob("*.sql"))
        assert paths, "the directory exists to hold migrations"

        numbers = []
        for path in paths:
            match = re.fullmatch(r"(\d{4})_[a-z0-9_]+\.sql", path.name)
            assert match, f"{path.name} is not NNNN_lower_snake_case.sql"
            numbers.append(match.group(1))

        assert len(set(numbers)) == len(numbers), "two migrations share a number"

    def test_init_db_leaves_nothing_pending(self, client):
        """A database built from schema.sql already contains everything the
        migrations do, so init-db records them and `migrate` is a no-op. Built
        here rather than leaning on the session's own setup, so the claim is
        tested rather than assumed."""
        from db import init_db

        init_db()

        assert migrations.pending() == []
        assert all(applied for _, applied in migrations.status())
