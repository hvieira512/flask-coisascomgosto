"""Guards for the element IDs the front-end JavaScript depends on.

These exist because a template rewrite silently broke the login page: a framework
migration dropped `id="form-header"` and `id="auth-container"`, and
`document.querySelector` returned null at runtime. Nothing else in the suite
caught it, because the server-rendered HTML was still perfectly valid — only the
browser knew it was broken. Any test here should name the JS file that would
break if the assertion fails.

What is deliberately *not* here any more: tests that read a JavaScript file and
asserted strings in it — the endpoints a page calls, the markup a template
literal contains, a particular line of code. They pass whether the page works or
not, and they fail whenever a line moves, which is the wrong way round on both
counts. Between them they never caught anything but my own renames. The behaviour
they claimed to protect is now checked where it happens: in a browser
(test_collection_form.py, test_dialog_behaviour.py), against the API, or against
a screenshot (test_appearance.py).
"""

import pathlib
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

    def test_no_token_helper_is_loaded(self, anon_client):
        """Signing in sets a cookie; there is no token for the page to keep."""
        html = anon_client.get("/auth").get_data(as_text=True)
        assert "js/core/auth.js" not in html


class TestDashboardHooks:
    """static/js/dashboard/menus.js and products/fetch.js query these."""

    def _login(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})

    def test_the_sidebar_is_an_offcanvas_the_burger_opens(self, client, make_user):
        """Bootstrap's offcanvas brings its own backdrop, which is why there is no
        #overlay element and no code of ours toggling one."""
        self._login(client, make_user)
        html = client.get("/dashboard/home").get_data(as_text=True)

        assert 'id="sidebar"' in html
        assert 'id="sidebarToggle"' in html
        assert 'class="offcanvas-lg offcanvas-start dash-sidebar"' in html
        assert 'data-bs-target="#sidebar"' in html
        assert 'id="overlay"' not in html

    def test_product_list_container_exists(self, client, make_user):
        """fetch.js renders into #product-list."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)
        assert 'id="product-list"' in html

    def test_modals_are_bootstraps(self, client, make_user):
        """Bootstrap's modal supplies the backdrop, the focus trap, Escape, the
        scroll lock and the fade; dismissing is its data-api. Opening is ours,
        because a form needs the record it is editing before it is any use, so
        there is no data-bs-toggle="modal" anywhere."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)

        assert 'class="modal fade dash-modal"' in html
        assert 'class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable"' in html
        assert 'data-bs-dismiss="modal"' in html
        assert 'data-bs-toggle="modal"' not in html
        assert "<dialog" not in html

    def test_nothing_wires_the_chrome_by_hand(self, client, make_user):
        """The sidebar, the user menu, the tabs and the modals are all Bootstrap's
        data-api, which is why the page loads no chrome script of its own."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)

        assert "js/dashboard/menus.js" not in html
        assert not pathlib.Path("static/js/dashboard/menus.js").exists()

    def test_the_close_control_carries_an_accessible_name(self, client, make_user):
        """Bootstrap's .btn-close is a glyph and nothing else, so without the label
        a screen reader reads an unnamed button."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)

        assert 'class="btn-close"' in html
        assert 'aria-label="Fechar"' in html

    def test_no_token_helper_is_loaded(self, client, make_user):
        """The page modules call fetch() directly; the cookie rides along."""
        self._login(client, make_user)
        html = client.get("/dashboard/products").get_data(as_text=True)
        assert "js/core/auth.js" not in html


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
        for element_id in ["gallery-stage", "stage-image", "thumb-strip",
                           "stage-counter", "stage-zoom", "variant-options",
                           "size-options"]:
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
        # A modifier may follow the base class, e.g. "section is-medium".
        assert 'class="section' in body
        assert 'class="container' in body


class TestNotifications:
    """js/core/notify.js wraps SweetAlert2.

    SweetAlert2 is the one vendored library that only publishes a global, so it
    stays a classic script tag; notify.js is a module that reads Swal when a toast
    is actually raised, which is long after any script has finished loading. That
    is what removed the old "must load after" ordering rule."""

    def _dashboard(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/products").get_data(as_text=True)

    def test_auth_page_loads_sweetalert2(self, anon_client):
        html = anon_client.get("/auth").get_data(as_text=True)
        assert "sweetalert2/sweetalert2.all.min.js" in html

    def test_dashboard_loads_sweetalert2(self, client, make_user):
        assert "sweetalert2/sweetalert2.all.min.js" in self._dashboard(client, make_user)

    def test_notify_is_imported_rather_than_loaded(self, anon_client):
        html = anon_client.get("/auth").get_data(as_text=True)
        assert "js/core/notify.js" not in html

        source = pathlib.Path("static/js/auth/auth.js").read_text(encoding="utf-8")
        assert 'import { Notify }' in source

    def test_notify_reads_swal_lazily(self):
        """It must not capture Swal at module evaluation: a module runs before the
        classic vendor script has necessarily been parsed."""
        source = pathlib.Path("static/js/core/notify.js").read_text(encoding="utf-8")
        assert 'typeof Swal === "undefined"' in source

    @pytest.mark.parametrize("path", ["/", "/products", "/not-found"])
    def test_storefront_stays_lean(self, client, path):
        """No public page notifies, so none should carry the 77KB library. It
        used to sit in the shared base template and load on every page."""
        html = client.get(path).get_data(as_text=True)
        assert "sweetalert2" not in html


class TestColorScheme:
    """Every page must pin the light scheme.

    Bootstrap 5.3 carries a full dark palette under `[data-bs-theme=dark]`, and
    its components read their colours from those variables. The shop is a warm
    paper palette with no dark counterpart, so the scheme is declared rather than
    left to whatever the visitor's machine is set to.
    """

    @pytest.mark.parametrize(
        "path", ["/", "/products", "/auth", "/not-found"]
    )
    def test_html_pins_the_light_scheme(self, anon_client, path):
        """Anonymous: /auth redirects a signed-in visitor to the dashboard."""
        html = anon_client.get(path).get_data(as_text=True)
        assert 'data-bs-theme="light"' in html, f"{path} leaves the scheme open"

    def test_product_page_pins_the_light_scheme(self, client, make_product):
        product = make_product("Caixa")
        html = client.get(f"/products/{product['id']}").get_data(as_text=True)
        assert 'data-bs-theme="light"' in html

    def test_dashboard_pins_the_light_scheme(self, client):
        """The dashboard has its own base template, so it needs its own guard."""
        with client.session_transaction() as flask_session:
            flask_session["user"] = {"id": 1, "username": "admin"}

        html = client.get("/dashboard/home").get_data(as_text=True)
        assert 'data-bs-theme="light"' in html


class TestColorSetBadges:
    """js/store/color-set.js renders colour sets for the catalogue cards, the
    product page and the dashboard. It used to be a global that each page had to
    load first; it is imported now, so the pages that draw a badge say so."""

    def test_every_page_that_draws_a_badge_imports_it(self):
        """Found rather than listed: a hardcoded list has to be edited when a badge
        moves, and it went stale the first time one did — images.js stopped drawing
        them when the colours and photographs panels became one."""
        users, importers = set(), set()
        for path in sorted(pathlib.Path("static/js").rglob("*.js")):
            source = path.read_text(encoding="utf-8")
            if "ColorSet." in source:
                users.add(path.as_posix())
            if "import { ColorSet }" in source:
                importers.add(path.as_posix())

        assert users, "nothing draws a colour set badge any more?"
        assert users - importers == set(), f"draws a badge without importing: {users - importers}"

    def test_it_is_no_longer_a_script_tag(self, client, make_product):
        product = make_product("Caixa")
        for page in ["/products", f"/products/{product['id']}"]:
            html = client.get(page).get_data(as_text=True)
            assert "js/store/color-set.js" not in html, page


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
                           "deleteProductModal"]:
            assert f'id="{element_id}"' in html, element_id

    def test_there_is_no_read_only_product_modal(self, client, make_user):
        """Rows open straight into the edit modal, whose Detalhes tab shows the
        same facts a separate view modal used to repeat."""
        assert 'id="viewProductModal"' not in self._page(client, make_user)

    def test_filter_bar_is_rendered(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["filter-q", "filter-type", "filter-collection",
                           "filter-photos", "filter-clear"]:
            assert f'id="{element_id}"' in html, element_id

    def test_the_page_loads_exactly_one_script(self, client, make_user):
        """Its module imports the rest — the colour-set helper, the placeholder,
        the modal — so the template no longer lists them in dependency order."""
        html = self._page(client, make_user)

        assert 'type="module" src="/static/js/dashboard/products/main.js"' in html
        assert "js/store/color-set.js" not in html
        assert "js/store/placeholder.js" not in html


class TestDashboardHome:
    def test_home_renders_analytics_hooks(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        html = client.get("/dashboard/home").get_data(as_text=True)

        for element_id in ["stat-cards", "missing-photos", "upcoming-events"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/home.js" in html


class TestDashboardTypes:
    """The types page is driven by js/dashboard/types/main.js."""

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/types").get_data(as_text=True)

    def test_hooks_exist(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["type-rows", "type-count", "new-type", "material-rows",
                           "material-count", "material-form", "material-name",
                           "newTypeModal", "editTypeModal", "deleteTypeModal"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/types/main.js" in html

    def test_tab_is_in_the_sidebar(self, client, make_user):
        html = self._page(client, make_user)
        assert "/dashboard/types" in html
        assert ">Tipos<" in html


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


class TestDashboardColors:
    """The colours page is driven by js/dashboard/colors/main.js."""

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/colors").get_data(as_text=True)

    def test_hooks_exist(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["set-rows", "set-count", "new-set", "color-rows",
                           "color-count", "color-form", "color-name", "color-hex",
                           "newSetModal", "editSetModal", "deleteSetModal",
                           "editColorModal", "deleteColorModal"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/colors/main.js" in html

    def test_tab_is_in_the_sidebar(self, client, make_user):
        html = self._page(client, make_user)
        assert "/dashboard/colors" in html
        assert ">Cores<" in html


class TestDashboardCollections:
    """The collections page is driven by js/dashboard/collections/main.js.

    Collections had full CRUD in the API from the beginning and no screen at all,
    which stopped mattering the moment they became the catalogue's front door: a
    cover nobody can set is the same as no cover.
    """

    def _page(self, client, make_user):
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        return client.get("/dashboard/collections").get_data(as_text=True)

    def test_hooks_exist(self, client, make_user):
        html = self._page(client, make_user)
        for element_id in ["collection-rows", "collection-count", "new-collection",
                           "newCollectionModal", "editCollectionModal",
                           "deleteCollectionModal"]:
            assert f'id="{element_id}"' in html, element_id
        assert "js/dashboard/collections/main.js" in html

    def test_tab_is_in_the_sidebar(self, client, make_user):
        html = self._page(client, make_user)
        assert "/dashboard/collections" in html
        assert "Colecções" in html


class TestSteppedCreateForms:
    """The two big create forms ask for the required fields first.

    Produto and Evento each have six controls of which two are required, so the
    create dialog walks them in groups. Nothing is written until the last step: a
    piece is on the storefront the moment its row exists, and there is no draft
    flag, so a half-answered form must not create one.
    """

    def _module(self, path):
        return pathlib.Path(path).read_text(encoding="utf-8")

    def test_the_forms_declare_their_groups(self):
        product = self._module("static/js/dashboard/products/form.js")
        for group in ['data-step="identity"', 'data-step="details"']:
            assert group in product, group

        event = self._module("static/js/dashboard/events/main.js")
        for group in ['data-step="when"', 'data-step="details"']:
            assert group in event, group

    def test_creating_is_stepped_and_editing_is_not(self):
        """Editing is changing one thing; a wizard would make you walk past
        three screens to fix a typo. The product edit modal keeps its tabs, which
        are random access, and the event edit modal keeps its single screen."""
        products = self._module("static/js/dashboard/products/main.js")
        assert 'id: "newProductModal"' in products
        assert products.count("stepDialog({") == 1
        assert "#edit-tabs" in products

        events = self._module("static/js/dashboard/events/main.js")
        assert events.count("stepDialog({") == 1
        assert events.count("formDialog({") == 1

    def test_nothing_is_written_before_the_last_step(self):
        steps = self._module("static/js/core/steps.js")
        assert "if (!last())" in steps
        assert "onFinish(root)" in steps

    def test_back_is_hidden_with_the_attribute(self):
        """Bootstrap ships `[hidden]{display:none!important}`, so the attribute is
        enough here. Under Bulma it was not — .button set its own display, which
        outranked [hidden], and Voltar sat there on the first step."""
        steps = self._module("static/js/core/steps.js")
        assert "back.hidden = index === 0" in steps

        bootstrap = pathlib.Path("static/bootstrap/bootstrap.min.css").read_text(
            encoding="utf-8"
        )
        assert "[hidden]{display:none!important}" in bootstrap

    def test_the_slide_has_a_reduced_motion_escape(self):
        css = pathlib.Path("static/css/dashboard.css").read_text(encoding="utf-8")
        assert "@keyframes step-in" in css
        assert "[data-step] {" in css
        reduced = css.split("prefers-reduced-motion: reduce")
        assert any("[data-step]" in block for block in reduced[1:])


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

    def test_the_navbar_is_fixed_and_the_page_reserves_room_for_it(self, client,
                                                                   make_user):
        """Bootstrap's .fixed-top takes the bar out of the flow and reserves
        nothing for it, so the padding is dashboard.css's own — and both have to
        agree on the height, which is why it is a variable."""
        html = self._page(client, make_user)
        assert 'class="navbar fixed-top dash-navbar"' in html

        css = pathlib.Path("static/css/dashboard.css").read_text(encoding="utf-8")
        assert "padding-top: var(--dash-navbar-height)" in css
        assert "--dash-navbar-height:" in css


class TestProductGallery:
    """PhotoSwipe ships ESM only, which is what first forced a module into a
    codebase of classic scripts. Now that everything is a module, the gallery
    imports the lightbox instead of finding it on window at click time."""

    def _page(self, client, make_product):
        product = make_product("Caixa")
        return client.get(f"/products/{product['id']}").get_data(as_text=True)

    def test_the_page_loads_exactly_one_script(self, client, make_product):
        html = self._page(client, make_product)

        assert 'type="module" src="/static/js/store/product.js"' in html
        assert "js/store/gallery.js" not in html
        assert "js/store/lightbox.js" not in html

    def test_photoswipe_styles_are_loaded(self, client, make_product):
        """The stylesheet cannot be imported by the module, so the template keeps
        it."""
        html = self._page(client, make_product)
        assert "photoswipe/photoswipe.css" in html

    def test_the_gallery_imports_the_lightbox(self):
        source = pathlib.Path("static/js/store/gallery.js").read_text(encoding="utf-8")
        assert 'import { StoreLightbox } from "./lightbox.js"' in source
        assert "window.StoreLightbox" not in source


class TestColorSetBadge:
    """The badge is rendered by both the storefront and the dashboard."""

    def test_styles_live_in_the_shared_stylesheet(self):
        """The dashboard loads only theme.css, so while these rules lived in
        store.css its badges rendered with no swatches at all.

        Anchored to the start of a line, so it pins where the *base* rule lives
        without forbidding a storefront-only override of it — the product page's
        variant chips carry larger swatches than a table row does.
        """
        import pathlib
        import re

        base_rule = re.compile(r"^\.swatch\s*\{", re.M)
        assert base_rule.search(pathlib.Path("static/css/theme.css").read_text())
        assert not base_rule.search(pathlib.Path("static/css/store.css").read_text())

    def test_the_catalog_renders_swatches_and_a_full_name(self, client, make_product,
                                                          make_color, make_color_set):
        """The name truncates in the catalog's column, so the title attribute is
        what makes the long ones readable. Asserted through the API the page
        renders from, rather than by grepping the script that builds it."""
        color = make_color("Vermelho", hex="#B3282D")
        color_set = make_color_set("Vermelho e Branco", [color["id"]])
        product = make_product("Caixa")
        client.post(f"/api/products/{product['id']}/variants",
                    json={"color_set_id": color_set["id"]})

        body = client.get(f"/api/products/{product['id']}").get_json()
        variant = body["variants"][0]

        assert variant["color_set"]["name"] == "Vermelho e Branco"
        assert variant["color_set"]["colors"][0]["hex"] == "#B3282D"


class TestOneModuleSystem:
    """Every script in static/js is an ES module.

    There used to be two systems: 17 modules and 8 classic scripts publishing on
    window. The cost was written into the code — core/api.js carried "core/auth.js
    is a classic script, so it cannot import from here and hardcodes
    /api/auth/refresh itself". A second URL, because of a module boundary.
    """

    @staticmethod
    def _sources():
        return sorted(pathlib.Path("static/js").rglob("*.js"))

    def test_nothing_publishes_itself_on_window(self):
        offenders = []
        for path in self._sources():
            for line in path.read_text(encoding="utf-8").splitlines():
                # window.Swal is SweetAlert2's own global, read not written.
                if re.match(r"\s*window\.[A-Z]\w*\s*=", line):
                    offenders.append(f"{path}: {line.strip()}")
        assert offenders == [], offenders

    def test_every_script_tag_is_a_module(self, client, make_user, make_product):
        """The exceptions are vendored bundles that only publish a global:
        SweetAlert2, Font Awesome's loader, and Bootstrap's own bundle — which has
        to be a classic script so its data-api is wired before any module runs."""
        make_user("dash", password="pw")
        client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
        product = make_product("Caixa")

        pages = ["/", "/products", f"/products/{product['id']}",
                 "/dashboard/home", "/dashboard/products", "/dashboard/types",
                 "/dashboard/colors", "/dashboard/collections", "/dashboard/events",
                 "/dashboard/contacts"]

        for page in pages:
            html = client.get(page).get_data(as_text=True)
            for tag in re.findall(r"<script[^>]*src=[^>]*>", html):
                if any(vendor in tag for vendor in
                       ("sweetalert2", "fontawesome", "bootstrap")):
                    continue
                assert 'type="module"' in tag, f"{page}: {tag}"


def test_no_template_syntax_from_another_language_in_the_markup_builders():
    """The dashboard builds its markup in JavaScript template literals, where a Jinja
    comment and a JSX comment are both just text — and both render.

    Written because it happened twice within an hour: `{/* … */}` in the wizard's
    colour step and `{# … #}` in the collections form. Neither is a syntax error, so
    nothing else notices until the words appear on screen.
    """
    offenders = []
    for path in sorted(pathlib.Path("static/js").rglob("*.js")):
        source = path.read_text(encoding="utf-8")
        for opener in ("{#", "{/*"):
            if opener in source:
                offenders.append(f"{path}: {opener}")

    assert offenders == [], offenders


def test_row_actions_reveal_on_any_row_not_only_a_table():
    """The rename and delete buttons on a row are hidden until it is hovered.

    The reveal used to name `.dash-table tbody tr:hover`, so the materials list —
    panel-blocks, not table rows — kept its buttons at opacity 0 at every mouse
    position. They were in the DOM and clickable, which is why nothing else
    noticed: the owners could add a material and never rename or delete one.
    """
    css = pathlib.Path("static/css/dashboard.css").read_text(encoding="utf-8")

    assert ":is(tr, li):hover .dash-row-actions" in css
    assert ".dash-table tbody tr:hover .dash-row-actions" not in css, (
        "scoping the reveal to one container is what broke it"
    )


def test_the_materials_panel_offers_the_full_set(client, make_user):
    """Adding, renaming and deleting a material all live on /dashboard/types."""
    make_user("dash", password="pw")
    client.post("/api/auth/login", json={"username": "dash", "password": "pw"})
    html = client.get("/dashboard/types").get_data(as_text=True)

    for hook in ["material-form", "material-name", "material-rows", "material-count"]:
        assert f'id="{hook}"' in html, hook


class TestStylesheetsParse:
    """A stray comment terminator silently deletes the rule after it.

    This happened: a comment reading "py-*/px-* would have to be repeated" closed
    itself at the `*/` in the middle, and the `.section` rule underneath became
    part of the garbage that followed — every storefront band lost its padding and
    the landing page scrolled 12px sideways on a phone. Nothing failed; the
    stylesheet still served with a 200.
    """

    @staticmethod
    def _sheets():
        return sorted(pathlib.Path("static/css").glob("*.css"))

    def test_every_comment_is_closed_exactly_once(self):
        for sheet in self._sheets():
            text = sheet.read_text(encoding="utf-8")
            assert text.count("/*") == text.count("*/"), (
                f"{sheet}: {text.count('/*')} comments opened, "
                f"{text.count('*/')} closed — a stray terminator eats the next rule"
            )

    def test_the_braces_balance(self):
        """The same failure the other way round: a rule left open takes the rest of
        the file with it."""
        for sheet in self._sheets():
            text = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"),
                          flags=re.S)
            assert text.count("{") == text.count("}"), sheet

    def test_the_storefront_bands_carry_their_padding(self, client):
        """The rule that went missing, asserted where it is used rather than only
        as a character count."""
        css = pathlib.Path("static/css/theme.css").read_text(encoding="utf-8")
        section = css[css.index(".section {"):]
        assert "padding: 3rem 1.5rem" in section[:120]

        html = client.get("/").get_data(as_text=True)
        assert 'class="section' in html
