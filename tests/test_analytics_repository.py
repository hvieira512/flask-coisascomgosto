"""The storefront event log, driven directly against a cursor.

Four kinds of event in one table, which is a shape that only stays honest if
something checks it: that each kind stores what it should, that the foreign keys
behave as the migration claims, and — the one that matters most — that the table
has no column capable of holding anything about a person.
"""

import pytest
from pymysql.err import IntegrityError

from repositories import AnalyticsRepository
from repositories.analytics import KINDS, normalise_term


@pytest.fixture()
def analytics(cursor):
    return AnalyticsRepository(cursor)


@pytest.fixture()
def piece(cursor):
    """A product with one colour, which is what a view or an enquiry points at."""
    from repositories import (
        ColorSetRepository,
        ProductTypeRepository,
        ProductRepository,
        ProductVariantRepository,
    )

    type_id = ProductTypeRepository(cursor).create(name="Caixa")
    product_id = ProductRepository(cursor).create(
        type_id=type_id, name="Caixa Redonda", description=""
    )
    color_set_id = ColorSetRepository(cursor).create(
        name="Preto e Dourado", color_ids=[]
    )
    variant_id = ProductVariantRepository(cursor).create(
        product_id=product_id, color_set_id=color_set_id
    )
    return {"product_id": product_id, "variant_id": variant_id}


def rows(cursor):
    """Every event, oldest first. A list, because fetchall() hands back a tuple
    and `== []` on a tuple is a confusing way to fail."""
    cursor.execute("SELECT * FROM storefront_events ORDER BY id")
    return list(cursor.fetchall())


class TestThePrivacyPromiseIsInTheSchema:
    """The migration says no identifiers are stored. A comment cannot enforce
    that, and the next person to add a column will not have read it."""

    def test_no_column_could_hold_an_identifier(self, cursor):
        cursor.execute("SHOW COLUMNS FROM storefront_events")
        columns = {row["Field"] for row in cursor.fetchall()}

        assert columns == {
            "id", "kind", "product_id", "variant_id", "size_id",
            "facet", "facet_label", "term", "results", "created_at",
        }, "a column was added to the event log — is it about a person?"

    @pytest.mark.parametrize(
        "forbidden",
        ["ip", "ip_address", "user_agent", "session", "session_id", "visitor",
         "visitor_id", "fingerprint", "email", "referrer"],
    )
    def test_the_obvious_names_are_absent(self, cursor, forbidden):
        cursor.execute("SHOW COLUMNS FROM storefront_events")
        columns = {row["Field"] for row in cursor.fetchall()}

        assert forbidden not in columns


class TestRecordingEachKind:
    def test_a_view_stores_the_piece_and_nothing_else(self, cursor, analytics, piece):
        analytics.record("view", product_id=piece["product_id"])

        (row,) = rows(cursor)
        assert row["kind"] == "view"
        assert row["product_id"] == piece["product_id"]
        assert (row["variant_id"], row["term"], row["facet"]) == (None, None, None)
        assert row["created_at"] is not None, "the default timestamp did not fire"

    def test_an_enquiry_stores_the_colour_and_size(self, cursor, analytics, piece):
        cursor.execute("SELECT id FROM sizes ORDER BY position LIMIT 1")
        size_id = cursor.fetchone()["id"]

        analytics.record(
            "enquiry",
            product_id=piece["product_id"],
            variant_id=piece["variant_id"],
            size_id=size_id,
        )

        (row,) = rows(cursor)
        assert row["variant_id"] == piece["variant_id"]
        assert row["size_id"] == size_id

    def test_a_search_stores_the_term_and_how_many_it_found(self, cursor, analytics):
        analytics.record("search", term="Caixa de Joias", results=0)

        (row,) = rows(cursor)
        assert row["term"] == "caixa de joias"
        assert row["results"] == 0, "zero results is the interesting case, not a null"

    def test_a_filter_stores_the_facet_and_its_label(self, cursor, analytics):
        analytics.record("filter", facet="tipo", facet_label="Caixa")

        (row,) = rows(cursor)
        assert (row["facet"], row["facet_label"]) == ("tipo", "caixa")

    def test_an_unknown_kind_is_refused(self, analytics):
        """Not a new kind to tolerate: the dashboard reads four names, so a fifth
        would pile up rows nobody ever looks at."""
        with pytest.raises(ValueError):
            analytics.record("clique")

    @pytest.mark.parametrize("kind", KINDS)
    def test_every_declared_kind_is_accepted(self, analytics, kind):
        analytics.record(kind)


class TestTheTermIsNormalised:
    """Two spellings of one search would split its count in the list the owners
    read."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Caixa", "caixa"),
            ("  caixa   redonda  ", "caixa redonda"),
            ("CAIXA\tDE\nJOIAS", "caixa de joias"),
        ],
    )
    def test_case_and_whitespace_collapse(self, raw, expected):
        assert normalise_term(raw) == expected

    def test_it_cannot_overflow_the_column(self, cursor, analytics):
        analytics.record("search", term="a" * 400, results=1)

        (row,) = rows(cursor)
        assert len(row["term"]) == 120


class TestWhatHappensWhenTheCatalogueChanges:
    def test_deleting_the_piece_takes_its_history(self, cursor, analytics, piece):
        """A view count for a piece that no longer exists answers nothing."""
        analytics.record("view", product_id=piece["product_id"])

        cursor.execute("DELETE FROM products WHERE id = %s", (piece["product_id"],))

        assert rows(cursor) == []

    def test_deleting_the_colour_keeps_the_enquiry(self, cursor, analytics, piece):
        """The question was asked, and it still counts for the piece."""
        analytics.record(
            "enquiry",
            product_id=piece["product_id"],
            variant_id=piece["variant_id"],
        )

        cursor.execute(
            "DELETE FROM product_variants WHERE id = %s", (piece["variant_id"],)
        )

        (row,) = rows(cursor)
        assert row["product_id"] == piece["product_id"]
        assert row["variant_id"] is None

    def test_an_invented_piece_is_refused_by_the_database(self, cursor, analytics):
        with pytest.raises(IntegrityError):
            analytics.record("view", product_id=9999)


class TestWhenCountingStarted:
    def test_it_is_none_before_anything_happens(self, analytics):
        assert analytics.counting_since() is None

    def test_it_is_the_first_event(self, analytics, piece):
        analytics.record("view", product_id=piece["product_id"])
        analytics.record("view", product_id=piece["product_id"])

        assert analytics.counting_since() is not None

    def test_counting_can_be_narrowed_to_one_kind(self, analytics, piece):
        analytics.record("view", product_id=piece["product_id"])
        analytics.record("search", term="caixa", results=2)

        assert analytics.count() == 2
        assert analytics.count("view") == 1
        assert analytics.count("enquiry") == 0
