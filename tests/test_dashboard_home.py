"""The dashboard's home page, in a real browser.

It used to be four counters and two lists, every one of which was a second copy of
what the page it linked to already showed. It now answers the question none of
those pages could: whether anybody looks at any of this.

The tests worth having are about what the page says when the numbers are awkward —
nothing recorded yet, a quiet week, a first week with nothing to compare against —
because those are the states that make a dashboard look broken.

`live_server` and `browser` come from conftest.py.
"""

import json

import pytest

pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def record():
    """Insert an event, optionally aged, committed on its own connection."""
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


@pytest.fixture()
def piece(client, make_product, make_color_set, make_color):
    product = make_product("Caixa Redonda")
    color_set = make_color_set("Preto e Dourado", [make_color("Preto")["id"]])
    variant = client.post(
        f"/api/products/{product['id']}/variants",
        json={"color_set_id": color_set["id"]},
    ).get_json()
    return {"product": product, "variant": variant}


@pytest.fixture()
def owner(browser, live_server, client, make_user):
    """The dashboard, signed in."""
    make_user("dash", password="Passw0rd!")

    context = browser.new_context(viewport={"width": 1280, "height": 1000})
    context.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "dash", "password": "Passw0rd!"}),
        headers={"Content-Type": "application/json"},
    )
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def open_home(days=None):
        suffix = f"?dias={days}" if days else ""
        page.goto(f"{live_server}/dashboard/home{suffix}")
        page.wait_for_selector("#totals [data-figure]")
        return page

    yield open_home, page, errors
    context.close()


class TestWhatIsGone:
    """Everything here was a copy of another page, and Hugo's own reading of it was
    that none of it was worth opening the dashboard for."""

    def test_the_page_no_longer_lists_pieces_without_photographs(self, owner):
        open_home, page, _ = owner
        open_home()

        assert page.locator("#missing-photos").count() == 0
        assert "sem fotografia" not in page.content()

    def test_the_page_no_longer_shows_events(self, owner):
        open_home, page, _ = owner
        open_home()

        assert page.locator("#upcoming-events").count() == 0
        assert "Próximos eventos" not in page.content()

    def test_the_four_counters_are_one_line(self, owner):
        open_home, page, _ = owner
        open_home()

        line = page.locator("#catalogue-line").inner_text()
        assert "peças" in line and "colecções" in line
        assert page.locator("#stat-cards").count() == 0

    def test_it_costs_one_request(self, owner):
        """It made six, two of them for lists it fetched twice."""
        open_home, page, _ = owner
        calls = []
        page.on("response", lambda r: calls.append(r.url) if "/api/" in r.url else None)

        open_home()
        page.wait_for_timeout(400)

        assert len(calls) == 1, calls
        assert "analytics/overview" in calls[0]


class TestBeforeAnythingIsRecorded:
    """The first thing the owners will see. Zeros that cannot say why are a page
    that looks broken."""

    def test_it_says_counting_has_not_started(self, owner):
        open_home, page, errors = owner
        open_home()

        assert "Ainda não há nada registado" in page.locator("#totals").inner_text()
        assert errors == []

    def test_it_says_it_once_rather_than_in_every_panel(self, owner):
        open_home, page, _ = owner
        open_home()

        assert page.content().count("Ainda não há nada registado") == 1

    def test_no_panel_pretends_to_have_data(self, owner):
        open_home, page, _ = owner
        open_home()

        for panel in ("most-viewed", "asked-colors", "top-filters"):
            assert page.locator(f"#{panel} li").count() == 0, panel

    def test_the_catalogue_line_leaves_out_the_start_date(self, owner):
        """There is no start date yet, and inventing today's would be a lie."""
        open_home, page, _ = owner
        open_home()

        assert "a contar desde" not in page.locator("#catalogue-line").inner_text()

    def test_no_figure_claims_a_change(self, owner):
        """Every count is zero and so is every previous count; an arrow either way
        would be noise."""
        open_home, page, _ = owner
        open_home()

        assert "vs. período anterior" not in page.locator("#totals").inner_text()


class TestWithSomethingRecorded:
    def test_the_totals_are_the_windows_own(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"], days_ago=40)
        open_home, page, errors = owner

        open_home(7)

        assert page.locator("[data-figure=views] .data").inner_text() == "1"
        assert errors == []

    def test_a_wider_window_takes_in_more(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"], days_ago=40)
        open_home, page, _ = owner

        open_home(90)

        assert page.locator("[data-figure=views] .data").inner_text() == "2"

    def test_a_change_against_the_previous_window_is_shown(
        self, owner, piece, record
    ):
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"])
        record("view", product_id=piece["product"]["id"], days_ago=9)
        open_home, page, _ = owner

        open_home(7)

        totals = page.locator("#totals").inner_text()
        assert "▲ 1 vs. período anterior" in totals

    def test_a_fall_is_shown_too(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"])
        for _ in range(4):
            record("view", product_id=piece["product"]["id"], days_ago=9)
        open_home, page, _ = owner

        open_home(7)

        assert "▼ 3 vs. período anterior" in page.locator("#totals").inner_text()

    def test_the_most_viewed_piece_is_listed_with_both_counts(
        self, owner, piece, record
    ):
        record("view", product_id=piece["product"]["id"])
        record("enquiry", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        row = page.locator("#most-viewed li").first.inner_text()
        assert "Caixa Redonda" in row
        assert "1 pedido" in row

    def test_a_piece_nobody_asked_about_says_so(self, owner, piece, record):
        """Openings without a single request is a different problem from nobody
        opening it, and the two columns beside each other are what makes it
        visible."""
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        assert "sem pedidos" in page.locator("#most-viewed li").first.inner_text()

    def test_the_piece_links_to_it_in_the_catalogue(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()
        page.locator("#most-viewed a").first.click()

        # The name is percent-encoded, so the assertion is on what the products
        # page made of it rather than on the shape of the query string.
        page.wait_for_url("**/dashboard/products?q=*")
        page.wait_for_selector("#product-list tr[data-product-id]")
        assert page.locator("#filter-q").input_value() == "Caixa Redonda"

    def test_the_colour_asked_for_is_named(self, owner, piece, record):
        record(
            "enquiry",
            product_id=piece["product"]["id"],
            variant_id=piece["variant"]["id"],
        )
        open_home, page, _ = owner

        open_home()

        assert "Preto e Dourado" in page.locator("#asked-colors").inner_text()

    def test_a_search_is_counted_without_being_quoted(self, owner, record):
        """The page shows how many searches there were and never what they said —
        the list of words that found nothing was not something Hugo wanted to
        read."""
        record("search", term="tabuleiro de queijos", results=0)
        open_home, page, _ = owner

        open_home()

        # The eyebrow labels are uppercased in CSS, so the rendered text is not the
        # string in the source.
        totals = page.locator("#totals").inner_text().lower()
        assert "procuras" in totals
        assert "tabuleiro" not in page.content()

    def test_the_filters_show_the_group_and_the_option(self, owner, record):
        record("filter", facet="Tipo", facet_label="Caixa")
        open_home, page, _ = owner

        open_home()

        filters = page.locator("#top-filters").inner_text()
        assert "Tipo" in filters and "Caixa" in filters

    def test_a_quiet_period_says_so_rather_than_showing_a_dash(
        self, owner, piece, record
    ):
        """Recording has started, so an empty panel is a fact about the period."""
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        assert "Ninguém perguntou por uma cor" in page.locator(
            "#asked-colors"
        ).inner_text()


class TestTheFiguresSayWhatTheyCount:
    """Hugo read the page and could not tell what it was telling him: "O que são as
    perguntas? O que são Vistas? Acessos ao website?" The labels are the answer,
    and so is the sentence under them."""

    def test_every_figure_is_there_and_named(self, owner, piece, record):
        record("visit")
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        labels = page.locator("#totals [data-figure]").all_inner_texts()
        assert len(labels) == 5
        joined = " ".join(labels).lower()
        for word in ("visitas", "aberturas de peças", "peças diferentes",
                     "pedidos de informação", "procuras"):
            assert word in joined, word

    def test_it_explains_an_opening_and_a_request(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        explanation = page.locator("#totals > .help").inner_text()
        assert "abrir a loja" in explanation
        assert "Pedir informações" in explanation

    def test_a_visit_is_not_the_same_as_an_opening(self, owner, piece, record):
        """Three arrivals, one of whom opened a piece — the pair of numbers is the
        whole point of counting visits."""
        for _ in range(3):
            record("visit")
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        assert page.locator("[data-figure=visits] .data").inner_text() == "3"
        assert page.locator("[data-figure=views] .data").inner_text() == "1"


class TestTheSparklines:
    """One line per figure, drawn by hand in SVG. A line is only worth drawing when
    there is a shape to see — a flat rule along the bottom of five cards is
    decoration, and it would read as "we measured this and it was nothing" on a
    page that has nothing yet."""

    def test_a_figure_with_data_gets_a_line(self, owner, piece, record):
        record("view", product_id=piece["product"]["id"], days_ago=2)
        record("view", product_id=piece["product"]["id"])
        open_home, page, errors = owner

        open_home()

        assert page.locator("#totals svg polyline").count() >= 1
        assert errors == []

    def test_nothing_recorded_draws_nothing(self, owner):
        open_home, page, _ = owner
        open_home()

        assert page.locator("#totals svg").count() == 0

    def test_a_figure_that_stayed_at_zero_draws_nothing(self, owner, piece, record):
        """Openings happened; nobody searched. The searches card keeps its zero and
        does not pretend to a trend."""
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home()

        assert page.locator("[data-figure=searches] svg").count() == 0
        assert page.locator("[data-figure=views] svg").count() == 1

    def test_the_line_has_one_point_per_day_of_the_window(
        self, owner, piece, record
    ):
        record("view", product_id=piece["product"]["id"])
        open_home, page, _ = owner

        open_home(30)

        points = page.locator("#totals svg polyline").first.get_attribute("points")
        assert len(points.split()) == 30


class TestWhatIsNewInTheCatalogue:
    """products.created_at only became true when migration 0011 ran. Until a window
    begins after it, the phrase is left out entirely rather than reporting the
    migration's own backfill as this week's work."""

    @pytest.fixture()
    def migrated_days_ago(self):
        from db import get_db_connection
        from repositories.analytics import CREATED_AT_MIGRATION

        with get_db_connection() as (_, cursor):
            cursor.execute(
                "SELECT applied_at FROM schema_migrations WHERE filename = %s",
                (CREATED_AT_MIGRATION,),
            )
            row = cursor.fetchone()

        assert row, f"{CREATED_AT_MIGRATION} is not recorded as applied"
        original = row["applied_at"]

        def move(days):
            with get_db_connection() as (_, cursor):
                cursor.execute(
                    "UPDATE schema_migrations SET applied_at = NOW() - INTERVAL %s DAY "
                    "WHERE filename = %s",
                    (days, CREATED_AT_MIGRATION),
                )

        yield move

        # conftest.py leaves schema_migrations alone between tests on purpose, so
        # this has to be undone here or it follows the suite around.
        with get_db_connection() as (_, cursor):
            cursor.execute(
                "UPDATE schema_migrations SET applied_at = %s WHERE filename = %s",
                (original, CREATED_AT_MIGRATION),
            )

    def test_the_line_says_nothing_while_it_cannot_be_said(self, owner, piece):
        open_home, page, _ = owner
        open_home()

        assert "nova" not in page.locator("#catalogue-line").inner_text()

    def test_a_new_piece_is_counted_once_the_dates_are_real(
        self, owner, piece, migrated_days_ago
    ):
        migrated_days_ago(60)
        open_home, page, _ = owner

        open_home(7)

        assert "1 nova" in page.locator("#catalogue-line").inner_text()


class TestTheWindowSelector:
    def test_it_opens_on_a_week(self, owner):
        open_home, page, _ = owner
        open_home()

        assert page.locator("[data-days][aria-pressed=true]").inner_text() == "7 dias"

    def test_choosing_one_puts_it_in_the_url(self, owner):
        open_home, page, _ = owner
        open_home()

        page.locator("[data-days='30']").click()

        page.wait_for_url("**dias=30")
        assert page.locator("[data-days][aria-pressed=true]").inner_text() == "30 dias"

    def test_a_reload_keeps_it(self, owner):
        open_home, page, _ = owner
        open_home(90)

        page.reload()
        page.wait_for_selector("#totals [data-figure]")

        assert page.locator("[data-days][aria-pressed=true]").inner_text() == "90 dias"

    def test_the_heading_says_which_period(self, owner):
        open_home, page, _ = owner
        open_home(30)

        assert "neste mês" in page.locator("#totals > .eyebrow").inner_text().lower()

    def test_an_invented_window_falls_back_to_a_week(self, owner):
        open_home, page, _ = owner
        open_home(999)

        assert page.locator("[data-days][aria-pressed=true]").inner_text() == "7 dias"


class TestOnAPhone:
    def test_it_does_not_scroll_sideways(self, browser, live_server, client, make_user):
        make_user("phone", password="Passw0rd!")
        context = browser.new_context(viewport={"width": 390, "height": 780})
        context.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "phone", "password": "Passw0rd!"}),
            headers={"Content-Type": "application/json"},
        )
        page = context.new_page()
        try:
            page.goto(f"{live_server}/dashboard/home")
            page.wait_for_selector("#totals [data-figure]")

            page.evaluate("() => window.scrollTo(300, 0)")

            assert page.evaluate("() => window.scrollX") == 0
        finally:
            context.close()
