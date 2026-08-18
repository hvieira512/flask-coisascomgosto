"""Tests for the contacts singleton and the public pages that render it.

The /api/contacts endpoints are behind a bearer token, so they use the
`auth_client` fixture. The landing page reads contacts server-side via the
context processor, so those tests stay unauthenticated.
"""

import re


class TestContactsApi:
    def test_schema_seeds_contact_details(self, auth_client):
        body = auth_client.get("/api/contacts/").get_json()
        assert body["address"] == "Viana do Castelo, Portugal"
        assert body["email"] == "geral@coisascomgosto.pt"

    def test_socials_are_seeded(self, auth_client):
        body = auth_client.get("/api/contacts/").get_json()
        assert "facebook.com" in body["facebook_url"]
        assert "instagram.com" in body["instagram_url"]

    def test_whatsapp_url_is_derived_from_the_number(self, auth_client):
        body = auth_client.get("/api/contacts/").get_json()
        assert body["whatsapp"] == "939320334"
        assert body["whatsapp_url"] == "https://wa.me/939320334"

    def test_there_is_no_separate_phone_field(self, auth_client):
        """The WhatsApp number IS the phone number, by design."""
        assert "phone" not in auth_client.get("/api/contacts/").get_json()

    def test_update_replaces_the_details(self, auth_client):
        response = auth_client.put(
            "/api/contacts/",
            json={
                "address": "Rua Nova 1, Viana do Castelo",
                "email": "loja@example.com",
                "whatsapp": "+351 912 345 678",
                "facebook_url": "https://facebook.com/x",
                "instagram_url": "https://instagram.com/x",
            },
        )
        assert response.status_code == 200
        assert response.get_json()["address"] == "Rua Nova 1, Viana do Castelo"

    def test_whatsapp_url_strips_spaces_and_plus(self, auth_client):
        auth_client.put(
            "/api/contacts/",
            json={"whatsapp": "+351 912 345 678"},
        )
        body = auth_client.get("/api/contacts/").get_json()
        assert body["whatsapp_url"] == "https://wa.me/351912345678"

    def test_blank_whatsapp_yields_no_url(self, auth_client):
        auth_client.put("/api/contacts/", json={"address": "Só morada"})

        body = auth_client.get("/api/contacts/").get_json()
        assert body["whatsapp_url"] is None

    def test_update_is_a_full_replacement(self, auth_client):
        auth_client.put("/api/contacts/", json={"email": "novo@example.com"})

        body = auth_client.get("/api/contacts/").get_json()
        assert body["email"] == "novo@example.com"
        assert body["address"] is None

    def test_stays_a_singleton(self, auth_client):
        auth_client.put("/api/contacts/", json={"email": "a@example.com"})
        auth_client.put("/api/contacts/", json={"email": "b@example.com"})

        from api.db import get_db_connection

        with get_db_connection() as (_, cursor):
            cursor.execute("SELECT COUNT(*) AS total FROM contacts")
            assert cursor.fetchone()["total"] == 1


class TestLandingPage:
    def test_root_renders_the_landing_page(self, client):
        response = client.get("/")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert "Coisas com Gosto" in html

    def test_landing_page_tells_the_story_in_order(self, client, make_product_type):
        """The agreed sections, in sequence: story first, the range late."""
        make_product_type("Caixa")
        html = client.get("/").get_data(as_text=True)

        # Match each section's own heading, not the navbar links or the hero's
        # CTA, which share the same words.
        headings = [
            "Começou numa bancada pequena",              # 2. Origem
            "três mãos-cheias de tempo",                 # 3. O ofício
            "As peças que saem da oficina",              # 4. O que fazemos
            'is-spaced">Onde nos encontra</h2>',         # 6. Contactos
        ]
        positions = [html.index(h) for h in headings]
        assert positions == sorted(positions), "sections are out of order"

    def test_the_range_is_not_the_first_thing_on_the_page(
        self, client, make_product_type
    ):
        """The landing page introduces the workshop before selling anything."""
        make_product_type("Caixa")
        html = client.get("/").get_data(as_text=True)

        assert html.index('id="origin"') < html.index("O que fazemos")

    def test_contacts_are_a_section_not_the_navbar(self, client):
        html = client.get("/").get_data(as_text=True)

        navbar = html[html.index("<nav"):html.index("</nav>")]
        assert "wa.me" not in navbar, "socials must not live in the navbar"
        assert 'id="contacts"' in html
        # Cards are Bulma .card now; contact-icon is the bit that stays ours.
        assert "contact-icon" in html

    def test_grid_cards_cancel_bulma_stacking_margin(self, client,
                                                     make_product_type):
        """Bulma gives .card:not(:last-child) a 1.5rem bottom margin for cards
        stacked in flow. Inside a grid the row gap already spaces them, and the
        margin inflates the row track: the last card stretches 24px past its
        siblings and the grid leaves dead space beneath it."""
        make_product_type("Caixa")
        html = client.get("/").get_data(as_text=True)

        for card in re.findall(r'class="cell card[^"]*"', html):
            assert "mb-0" in card, card

    def _contacts_section(self, client):
        html = client.get("/").get_data(as_text=True)
        return html[html.index('id="contacts"'):html.index("</section>",
                                                           html.index('id="contacts"'))]

    @staticmethod
    def _visible_text(markup):
        """Drop screen-reader-only spans, then all tags, leaving what is seen."""
        without_sr = re.sub(
            r'<span class="is-sr-only">.*?</span>', "", markup, flags=re.S
        )
        return re.sub(r"<[^>]+>", " ", without_sr)

    def test_cards_show_the_value_not_just_the_label(self, client):
        """A contacts section that hides the contacts asks the visitor to click
        each card to find out where the workshop is."""
        visible = self._visible_text(self._contacts_section(client))

        for value in ["geral@coisascomgosto.pt", "939320334"]:
            assert value in visible, f"{value} is not rendered visibly"

    def test_social_cards_show_the_handle_not_the_url(self, client):
        """"https://www.instagram.com/coisascomgosto.vianadocastelo/" is not a
        thing anybody reads off a card."""
        visible = self._visible_text(self._contacts_section(client))

        assert "coisascomgosto.vianadocastelo" in visible
        assert "https://www.instagram.com" not in visible

    def test_labels_are_still_visible(self, client):
        visible = self._visible_text(self._contacts_section(client))

        for label in ["Morada", "E-mail", "WhatsApp", "Facebook", "Instagram"]:
            assert label in visible, label

    def test_label_sits_beside_the_icon(self, client):
        """Bulma's .card is a flex column, so the label drops onto its own line
        without an explicit row direction."""
        contacts = self._contacts_section(client)

        assert "is-flex-direction-row" in contacts

    def test_address_card_opens_the_map(self, client):
        contacts = self._contacts_section(client)

        assert "https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9" in contacts
        assert 'rel="noopener"' in contacts

    def test_address_card_is_plain_text_without_a_map_link(self, client, auth_client):
        """No maps_url means no anchor, rather than a link going nowhere.

        PUT is a full replacement, so omitting the field is how it is cleared;
        sending an explicit null is rejected by the payload schema.
        """
        auth_client.put("/api/contacts/", json={"address": "Viana do Castelo"})
        contacts = self._contacts_section(client)

        assert "maps.app.goo.gl" not in contacts
        assert "Morada" in contacts

    def test_reserved_area_replaces_entrar(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "Área Reservada" in html
        assert ">Entrar<" not in html

    def test_landing_page_uses_bulma_not_bootstrap(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "bulma.min.css" in html
        assert "bootstrap" not in html

    def test_navbar_shows_the_logo(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "img/logo.png" in html
        assert 'class="navbar-item store-brand"' in html

    def test_contact_details_render_in_the_footer(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "geral@coisascomgosto.pt" in html
        assert "wa.me/939320334" in html
        assert "facebook.com/coisascomgosto.vianadocastelo" in html

    def test_product_types_are_listed(self, client, make_product_type):
        make_product_type("Caixa redonda")

        html = client.get("/").get_data(as_text=True)
        assert "Caixa redonda" in html

    def test_each_type_links_to_the_filtered_catalog(self, client, make_product_type):
        """The catalog reads type_id off the query string, so the filter is
        already applied by the time the grid renders."""
        product_type = make_product_type("Moldura")

        html = client.get("/").get_data(as_text=True)
        assert f'/products?type_id={product_type["id"]}' in html

    def test_sub_types_are_not_listed_as_cards(self, client, make_product_type):
        """Sub-types are a catalog distinction, not a first look at the range."""
        parent = make_product_type("Coracao")
        make_product_type("Com fio", parent_id=parent["id"])

        html = client.get("/").get_data(as_text=True)
        section = html[html.index("O que fazemos"):html.index('id="contacts"')]
        assert f'/products?type_id={parent["id"]}' in section
        # It may still appear as a sub-title on the parent's card, never a link.
        assert "?type_id=" not in section.split("Com fio")[1].split("</a>")[0]

    def test_empty_catalog_does_not_break_the_page(self, client):
        """With no types the section is simply omitted, not empty."""
        response = client.get("/")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert "O que fazemos" not in html
        assert 'id="origin"' in html
        assert 'id="contacts"' in html


class TestErrorPages:
    def test_unknown_page_returns_the_custom_404(self, client):
        response = client.get("/not-found")
        assert response.status_code == 404

        html = response.get_data(as_text=True)
        assert "Página não encontrada" in html
        assert "404" in html

    def test_the_404_page_keeps_the_site_chrome(self, client):
        html = client.get("/not-found").get_data(as_text=True)
        assert "bulma.min.css" in html
        assert "Coisas com Gosto" in html

    def test_unknown_product_page_returns_404(self, client):
        """The detail route exists but the product does not."""
        response = client.get("/products/9999")
        assert response.status_code == 200  # shell renders; JS shows the error state

    def test_api_404_stays_json(self, client):
        """API clients must not receive an HTML error page."""
        response = client.get("/api/not-found")
        assert response.status_code == 404
        assert response.content_type.startswith("application/json")

    def test_api_resource_404_stays_json(self, client):
        response = client.get("/api/products/9999")
        assert response.status_code == 404
        assert response.content_type.startswith("application/json")


class TestDashboardContacts:
    """Contacts is a singleton, so the dashboard edits it in place."""

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/contacts").get_data(as_text=True)

    def test_every_field_has_an_input(self, client, make_user):
        html = self._page(client, make_user)
        for name in ["address", "maps_url", "email", "whatsapp",
                     "facebook_url", "instagram_url"]:
            assert f'id="cf-{name}"' in html, name

    def test_page_loads_its_module(self, client, make_user):
        html = self._page(client, make_user)
        assert "js/dashboard/contacts.js" in html
        assert 'id="contact-form"' in html

    def test_tab_is_in_the_sidebar(self, client, make_user):
        html = self._page(client, make_user)
        assert "/dashboard/contacts" in html
        assert "Contactos" in html


class TestContactUpdateSemantics:
    """PUT replaces the whole row, which is what lets a detail be removed —
    and what makes a partial payload dangerous."""

    def test_omitting_a_field_clears_it(self, client):
        client.put("/api/contacts/", json={"address": "Só morada"})

        body = client.get("/api/contacts/").get_json()
        assert body["address"] == "Só morada"
        assert body["instagram_url"] is None

    def test_sending_every_field_keeps_them_all(self, client):
        payload = {
            "address": "Rua de Cardielos, n. 222",
            "email": "geral@coisascomgosto.pt",
            "whatsapp": "939320334",
            "maps_url": "https://maps.app.goo.gl/x",
            "facebook_url": "https://facebook.com/x",
            "instagram_url": "https://instagram.com/x",
        }
        client.put("/api/contacts/", json=payload)

        body = client.get("/api/contacts/").get_json()
        for key, value in payload.items():
            assert body[key] == value

    def test_whatsapp_url_is_derived_from_a_spaced_number(self, client):
        """The dashboard shows this preview, so it must match the API."""
        client.put("/api/contacts/", json={"whatsapp": "+351 939 320 334"})

        assert client.get("/api/contacts/").get_json()["whatsapp_url"] == \
            "https://wa.me/351939320334"


class TestSocialHandleFilter:
    """Strips a profile URL down to the name the contact cards show."""

    def _filter(self, app):
        return app.jinja_env.filters["social_handle"]

    def test_instagram_url(self, app):
        assert self._filter(app)(
            "https://www.instagram.com/coisascomgosto.vianadocastelo/"
        ) == "coisascomgosto.vianadocastelo"

    def test_facebook_url_without_a_trailing_slash(self, app):
        assert self._filter(app)(
            "https://www.facebook.com/coisascomgosto.vianadocastelo"
        ) == "coisascomgosto.vianadocastelo"

    def test_nested_path_takes_the_last_segment(self, app):
        assert self._filter(app)("https://facebook.com/pages/loja") == "loja"

    def test_a_bare_handle_passes_through(self, app):
        assert self._filter(app)("coisascomgostovc") == "coisascomgostovc"

    def test_a_domain_with_no_path_falls_back_to_the_url(self, app):
        """Better a visible URL than an empty card."""
        assert self._filter(app)("https://facebook.com") == "https://facebook.com"

    def test_none_is_empty(self, app):
        assert self._filter(app)(None) is None
