"""POST /api/storefront-events — the one endpoint the storefront writes to.

Public, because a visitor is not signed in and never will be, which makes it the
first unauthenticated write outside /auth. So the tests are mostly about what it
refuses and what it quietly ignores: a counter that puts an error in a shopper's
console is worse than a counter that missed one event.
"""

import pytest

URL = "/api/storefront-events/"


@pytest.fixture()
def piece(client, make_product, make_color_set):
    """A piece with a colour, which is what a view or an enquiry points at."""
    product = make_product("Caixa Redonda")
    color_set = make_color_set("Preto e Dourado")
    variant = client.post(
        f"/api/products/{product['id']}/variants",
        json={"color_set_id": color_set["id"]},
    )
    assert variant.status_code == 201, variant.get_json()
    return {"product": product, "variant": variant.get_json()}


def send(test_client, body, **headers):
    return test_client.post(
        URL, json=body, headers={"X-Requested-With": "fetch", **headers}
    )


def rows(cursor):
    cursor.execute("SELECT * FROM storefront_events ORDER BY id")
    return list(cursor.fetchall())


class TestItNeedsNoAccount:
    def test_an_anonymous_visitor_can_record_a_view(self, anon_client, piece):
        """The whole point: the visitor is a shopper, not an owner."""
        response = send(anon_client, {"kind": "view", "product_id": piece["product"]["id"]})

        assert response.status_code == 204
        assert response.get_data() == b""

    def test_the_header_is_required(self, anon_client, piece):
        """A crawler cannot set a header outside the CORS safelist, and a
        cross-site form cannot set one at all — the same reasoning as the guard on
        session writes."""
        response = anon_client.post(
            URL, json={"kind": "view", "product_id": piece["product"]["id"]}
        )

        assert response.status_code == 403


class TestWhatItRefuses:
    def test_an_unknown_kind_is_a_400(self, anon_client):
        response = send(anon_client, {"kind": "clique"})

        assert response.status_code == 400

    def test_the_message_names_the_kinds_it_takes(self, anon_client):
        """So whoever mistyped it can see the four without reading the source."""
        body = send(anon_client, {"kind": "clique"}).get_json()

        assert "view" in str(body) and "enquiry" in str(body)

    def test_a_missing_kind_is_a_400(self, anon_client):
        assert send(anon_client, {"product_id": 1}).status_code == 400


class TestWhatItQuietlyIgnores:
    def test_an_invented_piece_records_nothing(self, anon_client, cursor):
        """The piece may have been deleted between the page loading and this
        arriving. There is nothing to count and nothing to say."""
        response = send(anon_client, {"kind": "view", "product_id": 9999})

        assert response.status_code == 204
        assert rows(cursor) == []

    def test_another_pieces_colour_is_dropped_but_the_enquiry_is_kept(
        self, anon_client, cursor, piece, make_product, make_color_set, client
    ):
        """Losing the whole event would hide a client bug twice over."""
        other = make_product("Outra peça")
        other_set = make_color_set("Branco e Azul")
        other_variant = client.post(
            f"/api/products/{other['id']}/variants",
            json={"color_set_id": other_set["id"]},
        ).get_json()

        send(anon_client, {
            "kind": "enquiry",
            "product_id": piece["product"]["id"],
            "variant_id": other_variant["id"],
        })

        (row,) = rows(cursor)
        assert row["kind"] == "enquiry"
        assert row["product_id"] == piece["product"]["id"]
        assert row["variant_id"] is None

    def test_a_colour_with_no_piece_is_dropped(self, anon_client, cursor, piece):
        send(anon_client, {"kind": "enquiry", "variant_id": piece["variant"]["id"]})

        (row,) = rows(cursor)
        assert row["variant_id"] is None

    def test_an_invented_size_is_dropped(self, anon_client, cursor, piece):
        send(anon_client, {
            "kind": "enquiry",
            "product_id": piece["product"]["id"],
            "size_id": 9999,
        })

        (row,) = rows(cursor)
        assert row["kind"] == "enquiry"
        assert row["size_id"] is None


class TestWhatEachKindStores:
    def test_an_enquiry_carries_the_colour_and_size(
        self, anon_client, cursor, piece, client
    ):
        sizes = client.get("/api/sizes/").get_json()["sizes"]

        send(anon_client, {
            "kind": "enquiry",
            "product_id": piece["product"]["id"],
            "variant_id": piece["variant"]["id"],
            "size_id": sizes[0]["id"],
        })

        (row,) = rows(cursor)
        assert row["variant_id"] == piece["variant"]["id"]
        assert row["size_id"] == sizes[0]["id"]

    def test_a_search_carries_its_term_and_result_count(self, anon_client, cursor):
        send(anon_client, {"kind": "search", "term": "  Caixa   AZUL ", "results": 0})

        (row,) = rows(cursor)
        assert row["term"] == "caixa azul", "the term is normalised on the way in"
        assert row["results"] == 0

    def test_a_filter_carries_the_facet_and_label(self, anon_client, cursor):
        send(anon_client, {"kind": "filter", "facet": "Tipo", "facet_label": "Caixa"})

        (row,) = rows(cursor)
        assert (row["facet"], row["facet_label"]) == ("Tipo", "Caixa")


class TestTheFlood:
    """A public write with nothing in front of it. The limit costs a real shopper
    nothing — a visitor reading a piece sends one view and maybe an enquiry."""

    def test_the_event_after_the_allowance_is_refused(self, anon_client, piece):
        from api.rate_limit import events

        body = {"kind": "view", "product_id": piece["product"]["id"]}
        for attempt in range(events.allowed):
            assert send(anon_client, body).status_code == 204, attempt

        refused = send(anon_client, body)

        assert refused.status_code == 429

    def test_the_refusal_is_not_counted(self, anon_client, piece):
        """Otherwise somebody who keeps knocking keeps the window full, and a real
        visitor is refused for as long as they care to knock."""
        from api.rate_limit import events

        body = {"kind": "view", "product_id": piece["product"]["id"]}
        for _ in range(events.allowed + 5):
            send(anon_client, body)

        assert len(events._hits["127.0.0.1"]) == events.allowed

    def test_it_drains_on_its_own(self, anon_client, piece, monkeypatch):
        from api.rate_limit import events

        body = {"kind": "view", "product_id": piece["product"]["id"]}
        for _ in range(events.allowed):
            send(anon_client, body)
        assert send(anon_client, body).status_code == 429

        monkeypatch.setattr(events, "window_seconds", 0)

        assert send(anon_client, body).status_code == 204

    def test_a_refused_event_is_not_recorded(self, anon_client, cursor, piece):
        from api.rate_limit import events

        body = {"kind": "view", "product_id": piece["product"]["id"]}
        for _ in range(events.allowed + 3):
            send(anon_client, body)

        assert len(rows(cursor)) == events.allowed


class TestTheSwaggerDocument:
    def test_the_endpoint_is_documented_as_public(self, client):
        """No padlock: a shopper has no token, and a reader of the docs should not
        be told otherwise."""
        schema = client.get("/api/swagger.json").get_json()
        post = schema["paths"]["/storefront-events/"]["post"]

        assert "security" not in post
        assert "429" in post["responses"]
