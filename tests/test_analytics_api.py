"""GET /api/analytics/overview — what the dashboard's home page reads.

The window arithmetic is the part worth testing: everything on that page is "this
period against the one before it", and an off-by-one in either boundary would show
the owners a rise that was a fall. Events are inserted with explicit timestamps
rather than by driving a browser, so a test can put one nine days ago.
"""

import pytest

URL = "/api/analytics/overview"


@pytest.fixture()
def piece(client, make_product, make_color_set, make_color):
    product = make_product("Caixa Redonda")
    color_set = make_color_set("Preto e Dourado", [make_color("Preto")["id"]])
    variant = client.post(
        f"/api/products/{product['id']}/variants",
        json={"color_set_id": color_set["id"]},
    ).get_json()
    return {"product": product, "variant": variant, "color_set": color_set}


@pytest.fixture()
def record():
    """Insert an event, optionally aged.

    Aged because the repository always stamps NOW(), which is right for the
    application and useless for testing a window — a test needs an event nine days
    old.

    Its own connection per insert, so the row is committed: the endpoint answers
    on a connection of its own and cannot see another transaction's uncommitted
    work.
    """
    from db import get_db_connection

    def _record(kind, *, days_ago=0, **fields):
        columns = ["kind", "created_at"]
        values = ["%s", "NOW() - INTERVAL %s DAY"]
        params = [kind, days_ago]

        for column, value in fields.items():
            columns.append(column)
            values.append("%s")
            params.append(value)

        with get_db_connection() as (_, cursor):
            cursor.execute(
                f"INSERT INTO storefront_events ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)})",
                params,
            )

    return _record


class TestItIsTheOwnersReading:
    def test_a_stranger_cannot_have_it(self, anon_client):
        assert anon_client.get(URL).status_code == 401

    def test_the_owners_can(self, client):
        assert client.get(URL).status_code == 200


class TestTheWindow:
    def test_it_defaults_to_a_week(self, client):
        assert client.get(URL).get_json()["window"]["days"] == 7

    def test_it_takes_the_days_asked_for(self, client):
        assert client.get(f"{URL}?days=30").get_json()["window"]["days"] == 30

    @pytest.mark.parametrize("asked,expected", [(0, 1), (-5, 1), (9999, 365)])
    def test_it_is_clamped_rather_than_refused(self, client, asked, expected):
        """A hand-typed ?days=14 is a reasonable question; 400 for it would be
        pedantry, and 0 or 9999 still has to mean something."""
        response = client.get(f"{URL}?days={asked}")

        assert response.status_code == 200
        assert response.get_json()["window"]["days"] == expected

    def test_nonsense_falls_back_to_the_default(self, client):
        assert client.get(f"{URL}?days=abc").get_json()["window"]["days"] == 7

    def test_events_outside_it_are_not_counted(self, client, piece, record):
        record("view", product_id=piece["product"]["id"], days_ago=0)
        record("view", product_id=piece["product"]["id"], days_ago=9)

        body = client.get(f"{URL}?days=7").get_json()

        assert body["totals"]["views"] == 1

    def test_the_previous_window_is_the_one_before_it(self, client, piece, record):
        """Nine days ago is inside the previous week, not this one."""
        record("view", product_id=piece["product"]["id"], days_ago=1)
        record("view", product_id=piece["product"]["id"], days_ago=9)
        record("view", product_id=piece["product"]["id"], days_ago=10)

        body = client.get(f"{URL}?days=7").get_json()

        assert body["totals"]["views"] == 1
        assert body["previous"]["views"] == 2

    def test_the_two_windows_do_not_overlap(self, client, piece, record):
        """An event counted in both would show as a rise and a fall at once."""
        for day in range(0, 14):
            record("view", product_id=piece["product"]["id"], days_ago=day)

        body = client.get(f"{URL}?days=7").get_json()

        assert body["totals"]["views"] + body["previous"]["views"] == 14

    def test_counting_since_is_the_first_event_ever(self, client, piece, record):
        """Not the window: a quiet week and a week before recording began are
        different things, and the page says which."""
        record("view", product_id=piece["product"]["id"], days_ago=200)

        body = client.get(f"{URL}?days=7").get_json()

        assert body["totals"]["views"] == 0
        assert body["window"]["counting_since"] is not None

    def test_it_is_null_before_anything_is_recorded(self, client):
        assert client.get(URL).get_json()["window"]["counting_since"] is None


class TestTheTotals:
    def test_each_kind_is_counted_separately(self, client, piece, record):
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"])
        record("enquiry", product_id=piece["product"]["id"])
        record("search", term="caixa", results=3)
        record("filter", facet="Tipo", facet_label="Caixa")

        totals = client.get(URL).get_json()["totals"]

        assert totals["views"] == 2
        assert totals["enquiries"] == 1
        assert totals["searches"] == 1

    def test_pieces_counts_distinct_pieces_not_views(
        self, client, piece, record, make_product
    ):
        """How much of the catalogue got any attention at all."""
        other = make_product("Moldura Oval")
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=other["id"])

        totals = client.get(URL).get_json()["totals"]

        assert totals["views"] == 3
        assert totals["pieces"] == 2

    def test_an_empty_window_is_zeros_not_nulls(self, client):
        """SUM() over no rows is NULL, and the page has to print a number."""
        totals = client.get(URL).get_json()["totals"]

        assert totals == {"views": 0, "enquiries": 0, "searches": 0, "pieces": 0}


class TestMostViewed:
    def test_it_carries_the_name_and_both_counts(self, client, piece, record):
        record("view", product_id=piece["product"]["id"])
        record("enquiry", product_id=piece["product"]["id"])

        (row,) = client.get(URL).get_json()["top_products"]

        assert row["name"] == "Caixa Redonda"
        assert (row["views"], row["enquiries"]) == (1, 1)

    def test_it_is_ordered_by_views(self, client, piece, record, make_product):
        quiet = make_product("Moldura Oval")
        record("view", product_id=quiet["id"])
        for _ in range(3):
            record("view", product_id=piece["product"]["id"])

        names = [p["name"] for p in client.get(URL).get_json()["top_products"]]

        assert names == ["Caixa Redonda", "Moldura Oval"]

    def test_a_piece_asked_about_but_never_opened_still_appears(
        self, client, piece, record
    ):
        """Odd, but real: an enquiry from a shared link. Zero views and a question
        is worth seeing rather than dropping."""
        record("enquiry", product_id=piece["product"]["id"])

        (row,) = client.get(URL).get_json()["top_products"]

        assert (row["views"], row["enquiries"]) == (0, 1)


class TestWhatPeopleAskFor:
    def test_enquiries_are_grouped_by_colour(self, client, piece, record):
        record(
            "enquiry",
            product_id=piece["product"]["id"],
            variant_id=piece["variant"]["id"],
        )
        record(
            "enquiry",
            product_id=piece["product"]["id"],
            variant_id=piece["variant"]["id"],
        )

        (row,) = client.get(URL).get_json()["top_color_sets"]

        assert row["name"] == "Preto e Dourado"
        assert row["enquiries"] == 2

    def test_an_enquiry_with_no_colour_is_not_a_colour_anybody_asked_for(
        self, client, piece, record
    ):
        record("enquiry", product_id=piece["product"]["id"])

        assert client.get(URL).get_json()["top_color_sets"] == []


class TestWhatPeopleCouldNotFind:
    def test_only_the_searches_that_found_nothing(self, client, record):
        record("search", term="caixa", results=4)
        record("search", term="tabuleiro", results=0)

        (row,) = client.get(URL).get_json()["empty_searches"]

        assert row["term"] == "tabuleiro"
        assert row["count"] == 1

    def test_the_same_words_are_one_row(self, client, record):
        for _ in range(3):
            record("search", term="tabuleiro", results=0)

        (row,) = client.get(URL).get_json()["empty_searches"]

        assert row["count"] == 3


class TestWhichFiltersGetUsed:
    def test_they_are_grouped_by_facet_and_label(self, client, record):
        record("filter", facet="Tipo", facet_label="Caixa")
        record("filter", facet="Tipo", facet_label="Caixa")
        record("filter", facet="Colecção", facet_label="Filigrana")

        rows = client.get(URL).get_json()["top_filters"]

        assert rows[0] == {"facet": "Tipo", "label": "Caixa", "count": 2}
        assert {"facet": "Colecção", "label": "Filigrana", "count": 1} in rows


class TestTheCatalogueLine:
    def test_it_rides_along_so_the_page_costs_one_request(self, client, piece):
        """The old page made six requests for less than this."""
        catalogue = client.get(URL).get_json()["catalogue"]

        assert catalogue["products"] == 1
        assert catalogue["color_sets"] == 1
        assert catalogue["colors"] >= 1
        assert catalogue["collections"] == 0
