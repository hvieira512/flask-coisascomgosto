"""Guards for the element IDs and wrappers the front-end JavaScript depends on.

These exist because a template rewrite silently broke the login page: the Bulma
migration dropped `id="form-header"` and `id="auth-container"`, and
`document.querySelector` returned null at runtime. Nothing else in the suite
caught it, because the server-rendered HTML was still perfectly valid — only the
browser knew it was broken.

Any test here should name the JS file that would break if the assertion fails.
"""

import re

import pytest


class TestLoginPageHooks:
    """static/js/auth/auth.js queries these by ID."""

    def test_form_header_id_exists(self, anon_client):
        """renderLoginForm/renderRegisterForm set formHeader.innerHTML."""
        html = anon_client.get("/auth").get_data(as_text=True)
        assert 'id="form-header"' in html

    def test_auth_container_id_exists(self, anon_client):
        """renderLoading('#auth-container') silently no-ops without it."""
        html = anon_client.get("/auth").get_data(as_text=True)
        assert 'id="auth-container"' in html

    def test_auth_form_and_username_field_exist(self, anon_client):
        html = anon_client.get("/auth").get_data(as_text=True)
        assert 'id="auth-form"' in html
        assert 'id="usernameField"' in html
        assert 'id="submitBtn"' in html

    def test_auth_js_is_loaded(self, anon_client):
        html = anon_client.get("/auth").get_data(as_text=True)
        assert "js/auth/auth.js" in html

    def test_token_helper_loads_before_page_modules(self, anon_client):
        """auth.js calls window.Auth.storeTokens, so core/auth.js must come first."""
        html = anon_client.get("/auth").get_data(as_text=True)
        assert html.index("js/core/auth.js") < html.index("js/auth/auth.js")


class TestDashboardHooks:
    """static/js/dashboard/menus.js and products/fetch.js query these."""

    def _login(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})

    def test_sidebar_and_overlay_ids_exist(self, client, make_user):
        self._login(client, make_user)
        html = client.get("/dashboard/home").get_data(as_text=True)
        assert 'id="sidebar"' in html
        assert 'id="overlay"' in html
        assert 'id="sidebarToggle"' in html

    def test_product_list_container_exists(self, client, make_user):
        """fetch.js renders into #product-list."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)
        assert 'id="product-list"' in html

    def test_modals_use_the_data_attribute_api(self, client, make_user):
        """Modals close via data-modal-close (menus.js) and open from
        products/main.js, which needs the product before it can build a body.
        Neither is Bootstrap's data-bs-*."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)
        assert "data-modal-close" in html
        assert "data-bs-" not in html

    def test_token_helper_loads_before_page_modules(self, client, make_user):
        """fetch.js calls window.Auth.authFetch."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)
        assert html.index("js/core/auth.js") < html.index("js/dashboard/products/main.js")


class TestStorefrontHooks:
    """static/js/store/*.js query these."""

    def test_catalog_ids_exist(self, client):
        html = client.get("/products").get_data(as_text=True)
        for element_id in ["product-grid", "active-filters", "filter-groups",
                           "filter-search", "clear-filters", "pagination"]:
            assert f'id="{element_id}"' in html, element_id

    def test_product_page_gallery_ids_exist(self, client, make_product):
        product = make_product("Caixa")
        html = client.get(f"/products/{product['id']}").get_data(as_text=True)
        for element_id in ["gallery-stage", "stage-image", "thumb-rail",
                           "stage-counter", "variant-options", "size-options"]:
            assert f'id="{element_id}"' in html, element_id


class TestPageLayoutWrappers:
    """Inner pages must supply their own section/container.

    base.html renders <main> bare so the landing page can use full-bleed
    sections; without a wrapper the catalog sidebar sits flush against the
    viewport edge.
    """

    def _main_block(self, html):
        match = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
        assert match, "no <main> element"
        return match.group(1)

    def test_catalog_wraps_content_in_a_container(self, client):
        body = self._main_block(client.get("/products").get_data(as_text=True))
        assert 'class="section' in body
        assert 'class="container' in body

    def test_product_page_wraps_content_in_a_container(self, client, make_product):
        product = make_product("Caixa")
        body = self._main_block(
            client.get(f"/products/{product['id']}").get_data(as_text=True)
        )
        assert 'class="section' in body
        assert 'class="container' in body

    def test_error_page_wraps_content_in_a_container(self, client):
        body = self._main_block(client.get("/not-found").get_data(as_text=True))
        # Bulma modifiers may follow the base class, e.g. "section is-medium".
        assert 'class="section' in body
        assert 'class="container' in body


class TestNotifications:
    """SweetAlert2 replaced toastr; js/core/notify.js wraps it.

    toastr required jQuery, which had no other consumer in the project, so both
    were removed. These assertions stop either creeping back and stop a page
    calling Notify before the library that backs it has loaded.
    """

    def _dashboard(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/products").get_data(as_text=True)

    def test_auth_page_loads_sweetalert2(self, anon_client):
        html = anon_client.get("/auth").get_data(as_text=True)
        assert "sweetalert2/sweetalert2.all.min.js" in html
        assert "js/core/notify.js" in html

    def test_dashboard_loads_sweetalert2(self, client, make_user):
        html = self._dashboard(client, make_user)
        assert "sweetalert2/sweetalert2.all.min.js" in html
        assert "js/core/notify.js" in html

    def test_notify_wrapper_loads_after_sweetalert2(self, anon_client):
        """notify.js reads Swal at definition time to warn if it is missing."""
        html = anon_client.get("/auth").get_data(as_text=True)
        assert html.index("sweetalert2.all.min.js") < html.index("js/core/notify.js")

    @pytest.mark.parametrize("path", ["/", "/products", "/nao-encontrado"])
    def test_storefront_stays_lean(self, client, path):
        """No public page notifies, so none should carry the 79KB library."""
        html = client.get(path).get_data(as_text=True)
        assert "sweetalert2" not in html

    @pytest.mark.parametrize("path", ["/", "/products", "/auth"])
    def test_toastr_and_jquery_are_gone(self, client, path):
        html = client.get(path).get_data(as_text=True)
        assert "toastr" not in html
        assert "jquery" not in html.lower()

    def test_dashboard_has_no_toastr_or_jquery(self, client, make_user):
        html = self._dashboard(client, make_user)
        assert "toastr" not in html
        assert "jquery" not in html.lower()

    def test_no_javascript_still_calls_toastr(self):
        """The library is gone, so a stray call would be a runtime crash."""
        import pathlib

        for script in pathlib.Path("static/js").rglob("*.js"):
            assert "toastr" not in script.read_text(), script


class TestColorScheme:
    """Every page must pin Bulma to its light scheme.

    Bulma 1.x ships a `prefers-color-scheme: dark` block that repaints the
    navbar, cards, inputs and borders near-black. theme.css only overrides the
    scheme hue and saturation, not its lightness, so on a machine set to dark
    mode that block wins and the warm paper palette is lost. `data-theme=light`
    on <html> is declared after the media query in bulma.min.css, so it wins.
    """

    @pytest.mark.parametrize(
        "path", ["/", "/products", "/auth", "/not-found"]
    )
    def test_html_pins_the_light_scheme(self, anon_client, path):
        """Anonymous: /auth redirects a signed-in visitor to the dashboard."""
        html = anon_client.get(path).get_data(as_text=True)
        assert 'data-theme="light"' in html, f"{path} would go dark in dark mode"

    def test_product_page_pins_the_light_scheme(self, client, make_product):
        product = make_product("Caixa")
        html = client.get(f"/products/{product['id']}").get_data(as_text=True)
        assert 'data-theme="light"' in html

    def test_dashboard_pins_the_light_scheme(self, client):
        """The dashboard has its own base template, so it needs its own guard."""
        with client.session_transaction() as flask_session:
            flask_session["user"] = {"id": 1, "username": "admin", "is_admin": True}

        html = client.get("/dashboard/home").get_data(as_text=True)
        assert 'data-theme="light"' in html


class TestColorSetBadges:
    """js/store/color-set.js renders colour sets for both the catalog cards and
    the product page, so it has to load before either."""

    def test_catalog_loads_swatches_first(self, client):
        html = client.get("/products").get_data(as_text=True)
        assert html.index("js/store/color-set.js") < html.index("js/store/products.js")

    def test_product_page_loads_swatches_first(self, client, make_product):
        product = make_product("Caixa")
        html = client.get(f"/products/{product['id']}").get_data(as_text=True)
        assert html.index("js/store/color-set.js") < html.index("js/store/product.js")


class TestDashboardProducts:
    """The products page is driven entirely by js/dashboard/products/*, which
    queries these hooks."""

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/products").get_data(as_text=True)

    def test_modals_and_list_container_exist(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["product-list", "product-count", "new-product",
                           "newProductModal", "editProductModal",
                           "deleteProductModal", "viewProductModal"]:
            assert f'id="{element_id}"' in html, element_id

    def test_colour_set_helper_loads_before_the_module(self, client, make_user):
        """The cards and the edit modal render colour-set badges."""
        html = self._page(client, make_user)
        assert html.index("js/store/color-set.js") < html.index("js/dashboard/products/main.js")

    def test_dados_tab_is_gone(self, client, make_user):
        html = self._page(client, make_user)
        assert "Dados" not in html
        assert "dashboard/stats" not in html


class TestDashboardHome:
    def test_home_renders_analytics_hooks(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        html = client.get("/dashboard/home").get_data(as_text=True)

        for element_id in ["stat-cards", "missing-photos", "upcoming-events"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/home.js" in html


class TestDashboardEvents:
    """The events page is driven by js/dashboard/events/main.js."""

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/events").get_data(as_text=True)

    def test_hooks_exist(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["event-rows", "event-count", "new-event",
                           "newEventModal", "editEventModal", "deleteEventModal"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/events/main.js" in html

    def test_tab_is_in_the_sidebar(self, client, make_user):
        html = self._page(client, make_user)
        assert "Eventos" in html
        assert "/dashboard/events" in html


class TestModalFormScoping:
    """The create and edit modals render forms with the same element ids, and a
    closed modal stays in the DOM. Reading a field by id alone found the create
    form, so editing an event posted a new one instead of updating it."""

    def _module(self, path):
        import pathlib

        return pathlib.Path(path).read_text()

    def test_events_submit_scopes_to_a_modal(self):
        source = self._module("static/js/dashboard/events/main.js")
        assert "submitEventForm(modalId)" in source
        assert 'modal(modalId).querySelector("#event-form")' in source
        assert 'document.getElementById("event-form")' not in source

    def test_products_submit_scopes_to_a_modal(self):
        source = self._module("static/js/dashboard/products/form.js")
        assert 'root.querySelector("#product-form")' in source
        assert 'document.getElementById("product-form")' not in source


class TestDashboardChrome:
    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/products").get_data(as_text=True)

    def test_sidebar_links_back_to_the_storefront(self, client, make_user):
        html = self._page(client, make_user)
        assert "Ver a loja" in html
        assert "dash-sidebar-foot" in html

    def test_notifications_are_gone(self, client, make_user):
        """Nothing produced them, so the bell promised something that did not
        exist."""
        html = self._page(client, make_user)
        assert "fa-bell" not in html
        assert "dash-badge" not in html

    def test_navbar_uses_bulma_fixed_top(self, client, make_user):
        """The shell relies on Bulma's own fixed navbar, which needs
        has-navbar-fixed-top on <html> for the page padding to match."""
        html = self._page(client, make_user)
        assert "navbar is-fixed-top" in html
        assert 'class="has-navbar-fixed-top"' in html


class TestProductGallery:
    """The gallery is a classic script; PhotoSwipe ships ESM only, so the
    lightbox is a module that publishes window.StoreLightbox for it."""

    def _page(self, client, make_product):
        product = make_product("Caixa")
        return client.get(f"/products/{product['id']}").get_data(as_text=True)

    def test_lightbox_is_loaded_as_a_module(self, client, make_product):
        html = self._page(client, make_product)
        assert 'type="module" src="/static/js/store/lightbox.js"' in html

    def test_photoswipe_styles_are_loaded(self, client, make_product):
        html = self._page(client, make_product)
        assert "photoswipe/photoswipe.css" in html

    def test_gallery_still_loads_before_the_page_module(self, client, make_product):
        html = self._page(client, make_product)
        assert html.index("js/store/gallery.js") < html.index("js/store/product.js")


class TestColorSetBadgeMarkup:
    def _source(self):
        import pathlib

        return pathlib.Path("static/js/store/color-set.js").read_text()

    def test_badge_carries_the_full_name_as_a_title(self):
        """The catalog constrains badges to a column, so the longest names
        truncate; the title is what makes them readable on hover."""
        assert 'title="${escapeHtml(colorSet.name)}"' in self._source()

    def test_label_is_wrapped_so_it_can_truncate(self):
        assert 'class="color-set-name"' in self._source()

    def test_catalog_badges_are_left_aligned(self):
        """Bulma's .tag centres its content, which gave every label a different
        offset inside a fixed-width badge and made the circles zigzag down the
        column."""
        import pathlib

        css = pathlib.Path("static/css/store.css").read_text()
        block = css.split(".swatch-row .color-set-badge {")[1].split("}")[0]
        assert "justify-content: flex-start" in block
