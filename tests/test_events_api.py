"""Tests for events and the landing-page timeline.

Reads are public (the timeline needs them); writes require a bearer token.
"""

import pytest


@pytest.fixture()
def make_event(auth_client):
    def _make(name="Feira de Artesanato", starts_on="2025-08-12", **fields):
        payload = {"name": name, "starts_on": starts_on}
        payload.update({k: v for k, v in fields.items() if v is not None})
        response = auth_client.post("/api/events/", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


class TestEventsApi:
    def test_empty_database_returns_empty_page(self, client):
        body = client.get("/api/events/").get_json()
        assert body["events"] == []
        assert body["pagination"]["total"] == 0

    def test_create_and_read_back(self, client, make_event):
        created = make_event("Mostra de Artesanato", "2025-08-12",
                             location="Viana do Castelo")
        body = client.get(f"/api/events/{created['id']}").get_json()

        assert body["name"] == "Mostra de Artesanato"
        assert body["location"] == "Viana do Castelo"

    def test_year_is_derived_from_the_start_date(self, client, make_event):
        created = make_event(starts_on="2023-05-01")
        assert created["year"] == "2023"

    def test_optional_fields_default_to_null(self, client, make_event):
        created = make_event()
        assert created["ends_on"] is None
        assert created["url"] is None

    def test_listed_most_recent_first(self, client, make_event):
        make_event("Antiga", "2021-06-01")
        make_event("Recente", "2025-06-01")
        make_event("Intermédia", "2023-06-01")

        names = [e["name"] for e in client.get("/api/events/").get_json()["events"]]
        assert names == ["Recente", "Intermédia", "Antiga"]

    def test_search_matches_name_or_location(self, client, make_event):
        make_event("Feira do Livro", "2025-01-01", location="Porto")
        make_event("Mercado de Natal", "2025-12-01", location="Braga")

        by_name = client.get("/api/events/?q=Livro").get_json()
        by_place = client.get("/api/events/?q=Braga").get_json()
        assert [e["name"] for e in by_name["events"]] == ["Feira do Livro"]
        assert [e["name"] for e in by_place["events"]] == ["Mercado de Natal"]

    def test_update_changes_the_event(self, client, auth_client, make_event):
        created = make_event("Nome antigo", "2025-01-01")

        response = auth_client.put(
            f"/api/events/{created['id']}",
            json={"name": "Nome novo", "starts_on": "2025-01-01"},
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == "Nome novo"

    def test_delete_removes_it(self, client, auth_client, make_event):
        created = make_event()
        assert auth_client.delete(f"/api/events/{created['id']}").status_code == 200
        assert client.get(f"/api/events/{created['id']}").status_code == 404

    def test_unknown_id_returns_404(self, client):
        assert client.get("/api/events/9999").status_code == 404

    def test_missing_required_fields_return_400(self, auth_client):
        assert auth_client.post("/api/events/", json={"name": "Sem data"}).status_code == 400
        assert auth_client.post("/api/events/", json={"starts_on": "2025-01-01"}).status_code == 400


class TestEventGuards:
    def test_reads_are_public(self, client):
        assert client.get("/api/events/").status_code == 200

    def test_writes_require_a_token(self, client):
        assert client.post(
            "/api/events/", json={"name": "X", "starts_on": "2025-01-01"}
        ).status_code == 401

    def test_delete_requires_a_token(self, client, make_event):
        created = make_event()
        assert client.delete(f"/api/events/{created['id']}").status_code == 401


class TestTimelineSection:
    def test_timeline_is_omitted_when_there_are_no_events(self, client):
        """An empty rail would look broken, so the section is dropped entirely."""
        html = client.get("/").get_data(as_text=True)
        assert 'id="events"' not in html
        assert "Onde já estivemos" not in html

    def test_timeline_renders_events(self, client, make_event):
        make_event("Feira de Artesanato", "2025-08-12", location="Viana do Castelo")

        html = client.get("/").get_data(as_text=True)
        assert 'id="events"' in html
        assert "Feira de Artesanato" in html
        assert "Viana do Castelo" in html

    def test_timeline_sits_between_the_range_and_contacts(self, client, make_event,
                                                         make_product_type):
        make_product_type("Caixa")
        make_event()

        html = client.get("/").get_data(as_text=True)
        assert html.index("O que fazemos") < html.index('id="events"')
        assert html.index('id="events"') < html.index('id="contacts"')

    def test_rail_is_a_focusable_scroll_container(self, client, make_event):
        """Keyboard users must be able to reach and scroll the horizontal rail."""
        make_event()
        html = client.get("/").get_data(as_text=True)

        assert 'id="timeline"' in html
        assert 'tabindex="0"' in html
        assert "aria-label=" in html

    def test_drag_script_is_loaded(self, client, make_event):
        """static/js/store/timeline.js adds click-and-drag to the rail."""
        make_event()
        assert "js/store/timeline.js" in client.get("/").get_data(as_text=True)

    def test_arrow_buttons_are_rendered(self, client, make_event):
        """Visitors who would rather not drag get previous/next controls."""
        make_event()
        html = client.get("/").get_data(as_text=True)

        assert "data-timeline-prev" in html
        assert "data-timeline-next" in html

    def test_arrows_use_font_awesome_chevrons(self, client, make_event):
        """Text glyphs like &#8249; render differently per platform font."""
        make_event()
        html = client.get("/").get_data(as_text=True)

        assert "fa-chevron-left" in html
        assert "fa-chevron-right" in html

    def test_rail_aligns_with_its_header(self, client, make_event):
        """The rail lives in the same .container as the header above it."""
        make_event()
        html = client.get("/").get_data(as_text=True)

        # A full-bleed wrapper previously pushed the rail 72px off.
        assert "timeline-viewport" not in html
        assert "timeline-shell" in html

    def test_event_link_is_rendered_when_present(self, client, make_event):
        make_event(url="https://example.com/feira")

        html = client.get("/").get_data(as_text=True)
        assert "https://example.com/feira" in html


class TestEventDatesFilter:
    """The Portuguese date-range filter used by the timeline."""

    def _filter(self, app):
        return app.jinja_env.filters["event_dates"]

    def test_single_day(self, app):
        assert self._filter(app)("2025-08-12") == "12 de Agosto de 2025"

    def test_range_within_one_month_collapses(self, app):
        assert self._filter(app)("2025-08-12", "2025-08-20") == "12 - 20 de Agosto de 2025"

    def test_range_across_months_keeps_both(self, app):
        assert (
            self._filter(app)("2025-07-28", "2025-08-03")
            == "28 de Julho - 3 de Agosto de 2025"
        )

    def test_range_across_years_keeps_both_years(self, app):
        assert (
            self._filter(app)("2024-12-28", "2025-01-03")
            == "28 de Dezembro de 2024 - 3 de Janeiro de 2025"
        )

    def test_same_start_and_end_reads_as_one_day(self, app):
        assert self._filter(app)("2025-08-12", "2025-08-12") == "12 de Agosto de 2025"

    def test_unparseable_value_falls_back_to_the_raw_string(self, app):
        """A bad date must not break the whole landing page."""
        assert self._filter(app)("not-a-date") == "not-a-date"

    def test_none_is_empty(self, app):
        assert self._filter(app)(None) == ""
